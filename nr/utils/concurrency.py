# Copyright (c) 2015-2016  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the follo  wing conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
'''
`nr.utils.concurrency` - Simplifying concurrency
================================================
'''

__all__ = ['Job', 'ThreadPool', 'EventQueue', 'Synchronizable', 'Clock',
           'InvalidStateError', 'Cancelled', 'Timeout', 'main_thread',
           'current_thread', 'as_completed', 'synchronized', 'notify',
           'notify_all', 'wait']

__author__ = 'Niklas Rosenstein <rosensteinniklas(at)gmail.com>'
__version__ = '0.9.6-dev'

import collections
import functools
import threading
import time
import traceback
import sys

try:
  import queue
except ImportError:
  import Queue as queue

## ===========================================================================
## current_thread, main_thread
## ===========================================================================

from threading import current_thread

main_thread = next(t for t in threading.enumerate()
  if isinstance(t, threading._MainThread))

## ===========================================================================
## Global Constants
## ===========================================================================

# Possible Job states.
PENDING = 'pending'
RUNNING = 'running'
ERROR = 'error'
SUCCESS = 'success'

# Job event types, additionally to ERROR, SUCCESS
EVENT_STARTED = 'started'
EVENT_FINISHED = 'finished'
EVENT_CANCELLED = 'cancelled'

## ===========================================================================
## Exceptions
## ===========================================================================

class InvalidStateError(Exception):
  ''' Raised by various `Job` methods. '''


class Cancelled(Exception):
  ''' Raised by `Job.wait()`. '''


class Timeout(Exception):
  ''' Raised by `Job.wait()` and `SynchronizedDeque.get()`. '''


class Empty(Exception):
  ''' Raised by `SynchronizedDeque.get()`. '''

## ===========================================================================
## Job, as_completed
## ===========================================================================

_Listener = collections.namedtuple('_Listener', 'callback once')
ExceptionInfo = collections.namedtuple('ExceptionInfo', 'type value tb')

class Job(object):
  '''
  This class represents a job that can be executed at any time
  from any thread either synchronous or asynchronous (ie. in a
  different thread of execution). A Job can be cancelled at any time,
  but the implementation must handle the cancellation flag gracefully.

  :param target: A callable accepting the :class:`Job` instance as
    its the first and only argument.
  :param name: An optional name for the Job. This is usually useful
    for debugging purposes.
  :param lock: An optional custom locking primitive. A non-recursive
    lock is used by default.
  :param print_exc: If True is specified for this parameter, then the
    Job will print exceptions occuring during the execution of the
    *target* callable. The exception is still saved in the
    :attr:`exception` property.

  A Job can have the following states:

  - `PENDING`
  - `RUNNING`
  - `ERROR`
  - `SUCCESS`

  A Job has the following events that can be listened to with the
  `Job.add_listener()` or `Job.listen()` method:

  - `EVENT_STARTED`
  - `EVENT_FINISHED`
  - `EVENT_CANCELLED`

  Note that `EVENT_FINISHED` is triggered even if `EVENT_CANCELLED`
  has already been triggered since a cancelled Job can also finish.

  .. attribute:: userdict

    A dictionary that can be filled with arbitrary data. If multiple
    threads access this dictionary, the :class:`Job` object should be
    synchronized using the :attr:`synchronized` function.

  .. attribute:: lock

    The locking synchronization primitive.

  .. attribute:: condition

    The condition synchronization primitive.

  .. attribute:: print_exc
  '''

  # Make the global constants and exception types available
  # on the Job class and instances of it.
  PENDING = PENDING
  RUNNING = RUNNING
  ERROR = ERROR
  SUCCESS = SUCCESS
  EVENT_STARTED = EVENT_STARTED
  EVENT_FINISHED = EVENT_FINISHED
  EVENT_CANCELLED = EVENT_CANCELLED
  Timeout = Timeout
  Cancelled = Cancelled
  InvalidState = InvalidStateError

  def __init__(self, target=None, name=None, lock=None, print_exc=True):
    super(Job, self).__init__()
    self.__target = target
    self.__state = PENDING
    self.__cancelled = False
    self.__result = None
    self.__exception = None
    self.__listeners = {None: [], EVENT_STARTED: [], EVENT_FINISHED: [], EVENT_CANCELLED: []}
    self.__event_set = set()
    self.__event_lock = threading.Lock()
    self.__name = name
    self.userdict = {}
    self.lock = lock or threading.Lock()
    self.condition = threading.Condition(self.lock)
    self.print_exc = print_exc

  def __repr__(self):
    if self.__name:
      name = self.__name
    elif hasattr(self.__target, '__name__'):
      name = self.__target.__name__
    elif hasattr(self, 'name'):
      name = self.name
      if callable(name):
        name = name()
    else:
      name = None

    with self.lock:
      cancelled = self.__cancelled

    result = '<Job {0!r}'.format(name)
    if cancelled:
      result += ' cancelled '
    result += ' at 0x{0:x}'.format(id(self))
    with self.lock:
      result += ' , state: {0}>'.format(self.__state)
    return result

  @property
  def state(self):
    ''' The state of the job. '''

    with self.lock:
      return self.__state

  @property
  def result(self):
    '''
    The result of the jobs execution. Accessing this property while
    the job is pending or running will raise an `InvalidStateError`. If
    an exception occured during the jobs execution, it will be raised
    from accessing this property.
    '''

    with self.lock:
      if self.__state in (PENDING, RUNNING):
        raise InvalidStateError('job is {0}'.format(self.__state))
      elif self.__state == ERROR:
        reraise(*self.__exception)
      elif self.__state == SUCCESS:
        return self.__result
      else:
        raise RuntimeError('invalid job state {0!r}'.format(self.__state))

  @property
  def exception(self):
    '''
    The exception that occured while the job executed. Accessing
    this property while the job is pending or running will raise an
    `InvalidStateError`.
    '''

    with self.lock:
      if self.__state in (PENDING, RUNNING):
        raise InvalidStateError('job is {0}'.format(self.__state))
      elif self.__state == ERROR:
        assert self.__exception is not None
        return self.__exception
      elif self.__state in (RUNNING, SUCCESS):
        assert self.__exception is None
        return None
      else:
        raise RuntimeError('invalid job state {0!r}'.format(self.__state))

  @property
  def pending(self):
    ''' True if the job is pending. '''

    with self.lock:
      return self.__state == PENDING

  @property
  def running(self):
    ''' True if the job is running. '''

    with self.lock:
      return self.__state == RUNNING

  @property
  def finished(self):
    '''
    True if the job was run and is finished. This property sees
    no difference in when the job was sucessful or errored.
    '''

    with self.lock:
      return self.__state in (ERROR, SUCCESS)

  @property
  def cancelled(self):
    '''
    The flag that indicates if the job was cancelled. The job
    status can still be `ERROR` or `SUCCESS` if the job was cancelled.
    If it is successful, you can even read the `Job.result` that was
    returned when the job was cancelled, but keep in mind that `wait()`
    might raise `Cancelled` even if the job hasn't completed yet (for
    instance if it doesn't react on the cancellation and continues
    anyway).
    '''

    with self.lock:
      return self.__cancelled

  def _trigger_event(self, event):
    if event is None or event not in self.__listeners:
      raise ValueError('invalid event type: {0!r}'.format(event))
    with self.lock:
      # Check the event has not already been triggered, then mark
      # the event as triggered.
      if event in self.__event_set:
        raise RuntimeError('event already triggered: {0!r}'.format(event))
      self.__event_set.add(event)
      listeners = self.__listeners[event] + self.__listeners[None]

    # We use this lock to make sure that no callbacks for this Job
    # are called simultaneously.
    with self.__event_lock:
      for listener in listeners:
        # XXX: What to do on exceptions? Catch and make sure all listeners
        # run through? What to do with the exception(s) then?
        listener.callback(self, event)

  def get(self, default=None):
    '''
    Get the result of the Job, or return *default* if the Job state
    is not `SUCCESS`. Unlike accessing `Job.result`, this function will
    not raise a `RuntimeError` or re-raise the exception that happened
    in the Job's thread.

    *New in 0.9.6*
    '''

    with self.lock:
      if self.__state == SUCCESS:
        return self.__result
      else:
        return default

  def cancel(self):
    '''
    Sets the cancellation flag of the job. Note that a finished but
    cancelled Job will be in state `SUCCESS` or `ERROR`.
    '''

    cancelled = False
    with self.lock:
      if not self.__cancelled:
        self.__cancelled = True
        self.condition.notify_all()
        cancelled = True

    if cancelled:
      self._trigger_event(EVENT_CANCELLED)

  def add_listener(self, event, callback, once=False):
    '''
    Register a *callback* for the specified *event*. The function
    will be called with the :class:`Job` as its first parameter and the
    *event* name as the second.

    :param event: An event name or None to register the callback to be
      invoked for any event.
    :param callback: A function taking two arguments.
    :param once: If True is passed, the listener will be removed from
      the Job when it is re-started.
    '''

    if not callable(callback):
      raise TypeError('callback must be callable')

    if event not in self.__listeners:
      raise ValueError('invalid event type: {0!r}'.format(event))

    event_passed = False
    with self.lock:
      event_passed = (event in self.__event_set)
      if not (once and event_passed):
        self.__listeners[event].append(_Listener(callback, once))

    # If the event already happened, we'll invoke the callback
    # immediately to make up for what it missed.
    if event_passed:
      callback(self, event)

  def listen(self, event_names=None, once=False):
    '''
    Factory function for a function decorator that will add the
    function to the Job's listeners. *event_names* can be a function
    in order to decorate it immediately without requiring to actually
    call the `listen()` method with its parameters. Otherwise, it
    must be None to listen for all events, a single event name or a
    list of event names.
    '''

    if callable(event_names):
      return self.listen()(event_names)

    # We support multiple event types, but a single event type
    # may also be passed directly.
    if not isinstance(event_names, (tuple, list)):
      event_names = [event_names]

    for evname in event_names:
      if evname not in self.__listeners:
        raise ValueError('invalid event type: {0!r}'.format(evname))

    def decorator(func):
      for evname in event_names:
        self.add_listener(evname, func, once)
      return func
    return decorator

  def wait(self, raise_on_cancel=True, timeout=None):
    '''
    Wait for the job to finish.

    :param raise_on_cancel: If set to True, this parameter causes
      `Cancelled` to be raised when the Job was cancelled. If set
      to False, this function will block until the Job terminates
      even if it was cancelled.
    :raise Timeout: If a *timeout* was specified and the timeout was
      exceeded while waiting for the job to complete.
    :raise Cancelled: If `Job.cancelled` was set by calling `cancel()`.
      Note that you can still read the `Job.result` when it finished
      executing even if it was cancelled, but this function raises
      immediately when it was cancelled and the job might still be
      running (eg. if it doesn't react on the cancellation and
      continues anyway).
    '''

    start_t = time.time()
    with self.condition:
      while self.__state == RUNNING:
        if raise_on_cancel and self.__cancelled:
          break
        if timeout is None:
          self.condition.wait()
        else:
          time_passed = time.time() - start_t
          if time_passed > timeout:
            raise Timeout
          self.condition.wait(timeout - time_passed)
      if raise_on_cancel and self.__cancelled:
        raise Cancelled
    return self.result

  def start(self, as_thread=True, daemon=True, __state_check=True):
    '''
    Runs the job in a different thread if *as_thread* is True or
    in the current thread if it is False. Raises `InvalidStateError`
    if the job is already running.

    **Important**: If the Job is cancelled before it is started, the
    function will return None and no thread object if *as_thread* is
    True, since the Job will not be started at all. The result will
    be set to None.

    This function will remove all listeners that have been registered
    with the *once* flag.
    '''

    if __state_check:
      # We need to manually manage the lock to be able to release it
      # pre-emptively when needed.
      with self.lock:
        if self.__cancelled and self.__state == PENDING:
          # Cancel in PENDING state. Do not run the target function at all.
          self.__state = SUCCESS
          assert self.__exception is None
          assert self.__result is None
          return None

        if self.__state == RUNNING:
          raise InvalidStateError('job is already running')
        elif self.__state not in (PENDING, ERROR, SUCCESS):
          raise RuntimeError('invalid job state {0!r}'.format(self.__state))

        # Reset the Job attributes.
        self.__state = RUNNING
        self.__cancelled = False
        self.__result = None
        self.__exception = None
        self.__event_set.clear()

        # Remove all listeners that have been registered with the
        # "once" flag set.
        for listeners in self.__listeners.values():
          listeners[:] = (l for l in listeners if not l.once)

    if as_thread:
      thread = threading.Thread(target=self.start, args=(False, False, False))
      thread.setDaemon(daemon)
      thread.start()
      return thread

    try:
      result = None
      exception = None
      try:
        self._trigger_event(EVENT_STARTED)
        result = self.run()
        state = SUCCESS
      except Exception:  # XXX: Catch BaseException?
        if self.print_exc:
          traceback.print_exc()
        exception = ExceptionInfo(*sys.exc_info())
        state = ERROR

      with self.lock:
        cancelled = self.__cancelled
        self.__result = result
        self.__exception = exception
        self.__state = state

      self._trigger_event(EVENT_FINISHED)
    finally:
      with self.condition:
        self.condition.notify_all()

  def run(self):
    '''
    Overwrite this method to implement the job. The value returned
    from this method is used as the jobs result. Exceptions will be
    caught and stored in the `Job.exception` field.
    '''

    if self.__target is not None:
      return self.__target(self)
    raise NotImplementedError

  @staticmethod
  def factory(start_immediately=True):
    '''
    This is a decorator function that creates new `Job`s with
    the wrapped function as the target.

    :param start_immediately: True if the factory should call
      `Job.start()` immediately or False if it should return the
      job in pending state.
    '''

    def decorator(func):
      def wrapper():
        job = Job(target=func)
        if start_immediately:
          job.start()
        return job
      return wrapper
    return decorator


def as_completed(jobs):
  ''' Generator function that yields the jobs in order of their
  completion. Attaches a new listener to each job. '''

  jobs = tuple(jobs)
  event = threading.Event()
  callback = lambda f, ev: event.set()
  [job.add_listener(EVENT_FINISHED, callback, once=True) for job in jobs]

  while jobs:
    event.wait()
    event.clear()

    jobs, finished = split_list_by(jobs, lambda x: x.finished)
    for job in finished:
      yield job

## ===========================================================================
## ThreadPool
## ===========================================================================

class ThreadPool(object):
  '''
  This class represents a pool of threads that can process jobs
  up to a certain number of maximum concurrent workers. Each submission
  will receive its own `Job` or you can submit a `Job` directly. The
  workers will be started right when the pool is created.

  .. code-block:: python

    with nr.utils.concurrency.ThreadPool(5) as pool:
      jobs = dict([pool.submit(url_open, [url]), url] for url in URLS)
      for job in nr.utils.concurrency.as_completed(jobs):
        url = jobs[job]
        try:
          result = job.result
        except Exception as exc:
          print("Error fetching", url, ":", exc)
        else:
          print("Successfully fetched", url)

  .. warning::

    You must make sure to call ThreadPool.shutdown() at some point,
    otherwise the application will not be able to exit as the workers
    are created as non-daemon threads.
  '''

  Timeout = Timeout

  class _Worker(threading.Thread):

    def __init__(self, queue):
      super(ThreadPool._Worker, self).__init__()
      self.__queue = queue
      self.lock = threading.Lock()
      self.current = None

    def run(self):
      while True:
        item = self.__queue.get()
        try:
          if item is None:
            break
          with self.lock:
            self.current = item
          item.start(as_thread=False)
        except:
          # Exception won't make the _Worker shut down.
          traceback.print_exc()
        finally:
          self.__queue.task_done()
          with self.lock:
            self.current = None

  def __init__(self, max_workers, name=None, print_exc=True):
    super(ThreadPool, self).__init__()
    self.__queue = SynchronizedDeque()
    self.__threads = [self._Worker(self.__queue) for i in range(max_workers)]
    self.__running = True
    self.name = name
    self.print_exc = print_exc
    [t.start() for t in self.__threads]

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, exc_tb):
    self.shutdown(wait=True)
    return False

  def __len__(self):
    return len(self.__queue)

  def current_jobs(self):
    '''
    Retrieves a snapshot of the Jobs that are currently being
    processed by the :class:`ThreadPool`. These jobs are no in the
    pool's queue.
    '''

    jobs = []
    for worker in self.__threads:
      with worker.lock:
        if worker.current:
          jobs.append(worker.current)
    return jobs

  def clear(self):
    '''
    Remove all jobs from the queue and return a list of all jobs
    that were still pending. This method does not call :meth:`Job.cancel`.
    If you want that, use :meth:`cancel_all` or call the method manually.
    '''

    with synchronized(self.__queue):
      jobs = self.__queue.snapshot()
      self.__queue.clear()
    return jobs

  def cancel_all(self):
    '''
    Much like :meth:`clear`, but also calls :meth:`Job.cancel` on
    all the jobs returned and on the jobs that are currently being
    processed by the worker threads.
    '''

    jobs = self.clear()
    [j.cancel() for j in jobs]
    [j.cancel() for j in self.current_jobs()]
    return jobs

  def submit(self, job_or_function, pass_job=True, args=(), kwargs=None, front=False):
    '''
    Submit a new :class:`Job` to the :class:`ThreadPool`.

    :param job_or_function: A :class:`Job` or callable object.
    :param pass_job: If True and *job_or_function* was passed a callable
      and no :class:`Job`, the actual job instance is passed to the
      function as its first parameter, otherwise it will be omitted.
    :param args: Additional positional arguments for the callable object.
    :param kwargs: Additional keyword arguments for the callable object.
    :param front: If True, the new job will be added to the front
      of the queue, thus be processed before any other job.
    :raise TypeError: If a :class:`Job` was passed and *args* or *kwargs*
      is not empty/None.
    :raise RuntimeError: If the :class:`ThreadPool` ain't running.
    '''

    if not self.__running:
      raise RuntimeError("ThreadPool ain't running")

    if isinstance(job_or_function, Job):
      if args or kwargs:
        raise TypeError('can not provide additional arguments for Job')
      job = job_or_function
      job.print_exc = self.print_exc
    elif callable(job_or_function):
      if kwargs is None:
        kwargs = {}
      if pass_job:
        target = lambda j: job_or_function(job, *args, **kwargs)
      else:
        target = lambda j: job_or_function(*args, **kwargs)
      job = Job(target, print_exc=self.print_exc)
    else:
      raise TypeError('expected Job or callable')

    if front:
      self.__queue.appendleft(job)
    else:
      self.__queue.append(job)
    return job

  def wait(self, timeout=None):
    '''
    Block until all jobs in the :class:`ThreadPool` are finished.
    Beware that this can make the program run into a deadlock if
    another thread adds new jobs to the pool.

    :raise Timeout: If the timeout is exceeded.
    '''

    if not self.__running:
      raise RuntimeError("ThreadPool ain't running")
    self.__queue.wait()

  def shutdown(self, wait=True):
    '''
    Shut down the :class:`ThreadPool`.

    :param wait: If True, wait until all worker threads end.
    '''

    if self.__running:
      for thread in self.__threads:
        assert thread.isAlive()
        self.__queue.append(None)
      self.__running = False

    if wait:
      # TODO SynchronizedDeque does not (yet?) support a join() method
      for thread in self.__threads:
        thread.join()

## ===========================================================================
## EventQueue
## ===========================================================================

class EventQueue(object):
  '''
  This class represents a collection of events that can then be
  fired one or all at a time from a specific thread. This is especially
  useful for threaded GUI applications.

  Every event has an event type which is just a name that identifies
  the kind of the event. There are two kinds of event types: Ones that
  can be queued multiple times and that may carry arbitrary event data
  and ones that can only be queued once, with no data attached.

  In non-strict mode, every event that has not been formerly declared
  is queable multiple times (or: not mergeable). If a mergeable event
  is already queued and another of that type is being queued, that new
  event is just dropped.
  '''

  EventType = collections.namedtuple('EventType', 'name mergeable')
  Event = collections.namedtuple('Event', 'type data timestamp')

  def __init__(self, strict=True, lock=None):
    super(EventQueue, self).__init__()
    self.strict = strict
    self.event_types = {}
    self.events = collections.deque()
    self.lock = lock or threading.Lock()

  def __repr__(self):
    with self.lock:
      return '<EventQueue with {0} queued events>'.format(len(self.events))

  def new_event_type(self, name, mergeable=False):
    ''' Declare a new event. May overwrite an existing entry. '''

    self.event_types[name] = self.EventType(name, mergeable)

  def add_event(self, name, data=None):
    '''
    Add an event of type *name* to the queue. May raise a
    `ValueError` if the event type is mergeable and *data* is not None
    or if *name* is not a declared event type (in strict mode).
    '''

    try:
      mergeable = self.event_types[name].mergeable
    except KeyError:
      if self.strict:
        raise ValueError('unknown event type {0!r}'.format(name))
      mergeable = False

    if mergeable and data is not None:
      raise ValueError('mergable event can not have data attached')

    with self.lock:
      if mergeable:
        # Check if such an event already exists.
        for ev in self.events:
          if ev.type == name:
            return

      self.events.append(self.Event(name, data, time.clock()))

  def pop_event(self):
    '''
    Pop the next queued event from the queue.

    :raise ValueError: If there is no event queued.
    '''

    with self.lock:
      if not self.events:
        raise ValueError('no events queued')
      return self.events.popleft()

  def pop_events(self):
    '''
    Pop all events and return a `collections.deque` object. The
    returned container can be empty. This method is preferred over
    `pop_event()` as it is much faster as the lock has to be acquired
    only once and also avoids running into an infinite loop during
    event processing.
    '''

    with self.lock:
      events = self.events
      self.events = collections.deque()
      return events

## ===========================================================================
## Synchronizable, synchronized, notify, notify_all, wait
## ===========================================================================

class Synchronizable(object):
  '''
  This is a base class for objects that can be synchronized
  using a condition variable. Use the `synchronized()` decorator
  for instance methods to synchronize the full function call.

  To interact with a `Synchronizable` instance, you can use its
  `Synchronizable.condition` member directly or use the function-style
  global functions `synchronized()`, `notify()`, `notify_all()` and
  `wait()`. The latter is preferred due to the improved readability.
  Compare:

  .. code-block:: python

    with synchronized(obj):
      while not some_condition(obj):
        wait(obj)
      # do stuff
      notify_all(obj)
    # ------------------------------
    with obj.condition:
      while not some_condition(obj):
        obj.condition.wait()
      # do stuff
      obj.condition.notify_all()

  '''

  lock_type = staticmethod(threading.RLock)
  condition_type = staticmethod(threading.Condition)

  def __new__(cls, *args, **kwargs):
    instance = super(Synchronizable, cls).__new__(cls)
    instance.lock = cls.lock_type()
    instance.condition = cls.condition_type(instance.lock)
    return instance


def synchronized(func_or_obj):
  '''
  Decorator or context manager for a `Synchronizable` instance. Apply
  this function as a decorator to an instance method of a `Synchronizable`
  subclass to synchronize the full function call. Use this function on
  a `Synchronizable` instance to retrieve the condition variable and use
  it in a with-context.

  .. code-block:: python

    class Package(Synchronizable):
      @synchronized
      def set_status(self, status):
        # ...

    with synchronized(obj):
      # ...
      obj.notify_all()
  '''

  if hasattr(func_or_obj, 'condition'):
    return func_or_obj.condition
  elif callable(func_or_obj):
    @functools.wraps(func_or_obj)
    def wrapper(self, *args, **kwargs):
      with self.condition:
        return func_or_obj(self, *args, **kwargs)
    return wrapper
  else:
    raise TypeError('expected Synchronizable instance or callable to decorate')


def notify(obj):
  ''' Call `condition.notify()` on a `Synchronizable` object. '''

  return obj.condition.notify()


def notify_all(obj):
  ''' Call `condition.notify_all()` on a `Synchronizable` object. '''

  return obj.condition.notify_all()


def wait(obj, timeout=None):
  ''' Call `condition.wait()` on a `Synchronizable` object. '''

  if timeout is None:
    return obj.condition.wait()
  else:
    return obj.condition.wait(timeout)

## ===========================================================================
## Collections
## ===========================================================================

class SynchronizedDeque(Synchronizable):
  ''' Thread-safe wrapper for the `collections.deque`. *New in 0.9.6*. '''

  Empty = Empty
  Timeout = Timeout

  def __init__(self, iterable=()):
    super(SynchronizedDeque, self).__init__()
    self._deque = collections.deque(iterable)
    self._tasks = 0

  def __iter__(self):
    raise RuntimeError('SynchronizedDeque does not support iteration')

  @synchronized
  def snapshot(self):
    return list(self._deque)

  @synchronized
  def __bool__(self):
    return bool(self._deque)

  @synchronized
  def __len__(self):
    return len(self._deque)

  @synchronized
  def clear(self):
    ''' Clears the queue. Note that calling :meth:`wait` immediately
    after clear can still block when tasks are currently being processed
    since this method only clears queued items. '''

    self._tasks -= len(self._deque)
    self._deque.clear()
    notify_all(self)

  @synchronized
  def append(self, x):
    try:
      return self._deque.append(x)
    finally:
      self._tasks += 1
      notify_all(self)

  @synchronized
  def appendleft(self, x):
    try:
      return self._deque.appendleft(x)
    finally:
      self._tasks += 1
      notify_all(self)

  @synchronized
  def extend(self, iterable):
    count = len(self._deque)
    try:
      return self._deque.extend(iterable)
    finally:
      self._tasks += len(self._deque) - count
      notify_all(self)

  @synchronized
  def extendleft(self, iterable):
    count = len(self._deque)
    try:
      return self._deque.extendleft(iterable)
    finally:
      self._tasks += len(self._deque) - count
      notify_all(self)

  @synchronized
  def pop(self):
    try:
      return self._deque.pop()
    finally:
      notify_all(self)

  @synchronized
  def popleft(self):
    try:
      return self._deque.popleft()
    finally:
      notify_all(self)

  @synchronized
  def rotate(self, n):
    return self._deque.rotate(n)

  @synchronized
  def task_done(self):
    if self._tasks == 0:
      raise RuntimeError('task_done() called too often')
    assert self._tasks > 0
    self._tasks -= 1
    notify_all(self)

  @synchronized
  def get(self, method='pop', block=True, timeout=None):
    '''
    If *block* is True, this method blocks until an element can be
    removed from the deque with the specified *method*. If *block* is
    False, the function will raise `Empty` if no element is available.
    If *timeout* is not None and the timeout is exceeded, `Timeout`
    is raised.
    '''

    if method not in ('pop', 'popleft'):
      raise ValueError('method must be "pop" or "popleft": {0!r}'.format(method))

    t_start = time.clock()
    while not self:
      if not block:
        raise self.Empty

      if timeout is None:
        wait(self)
      else:
        t_delta = time.clock() - t_start
        if t_delta > timeout:
          raise self.Timeout
        wait(self, timeout - t_delta)

    return getattr(self, method)()

  @synchronized
  def wait(self, timeout=None):
    ''' Wait until all tasks completed or *timeout* passed. '''

    t_start = time.clock()
    while self._tasks != 0:
      if timeout is None:
        wait(self)
      else:
        t_delta = time.clock() - t_start
        if t_delta > timeout:
          raise self.Timeout
        wait(self, timeout - t_delta)

## ===========================================================================
## Other utilities
## ===========================================================================

class Clock(object):
  '''
  This class is a utility to partition a main loop into chunks at
  a fixed framerate. This is useful for Game/UI main loops.

  :param seconds: The number of seconds to wait for each pass. Can
    be omitted if *fps* is specified.
  :param fps: The frame rate for the clock. Can be omitted if *seconds*
    is specified.
  '''

  def __init__(self, seconds=None, fps=None):
    if seconds is not None:
      seconds = float(seconds)
    elif fps is not None:
      seconds = 1.0 / float(fps)
    else:
      raise ValueError('seconds or fps must be specified')
    super(Clock, self).__init__()
    self.seconds = seconds
    self.last = -1

  def sleep(self):
    '''
    Sleeps until the interval has passed since the last time this
    function was called. This is a synonym for `__call__()`. The first
    time the function is called will return immediately and not block.
    Therefore, it is important to put the call at the beginning of the
    timed block, like this:

    .. code-block:: python

      clock = Clock(fps=50)
      while True:
        clock.sleep()
        # Processing ...
    '''

    current = time.time()
    if self.last < 0:
      self.last = current
      return

    delta = current - self.last
    if delta < self.seconds:
      time.sleep(self.seconds - delta)
      self.last = time.time()

  __call__ = sleep


def split_list_by(lst, key):
  '''
  Splits a list by the callable *key* where a negative result will
  cause the item to be put in the first list and a positive into the
  second list.
  '''

  first, second = [], []
  for item in lst:
    if key(item):
      second.append(item)
    else:
      first.append(item)
  return (first, second)


def reraise(tpe, value, tb=None):
  ''' Reraise an exception from an exception info tuple. '''

  Py3 = (sys.version_info[0] == 3)
  if value is None:
    value = tpe()
  if Py3:
    if value.__traceback__ is not tb:
      raise value.with_traceback(tb)
    raise value
  else:
      exec('raise tpe, value, tb')
