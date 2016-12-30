# Copyright (c) 2015-2017  Niklas Rosenstein
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
"""
This module provides a simple interface to creating and managing concurrent
tasks. Note that the module does not primarily focus on performance
multithreading, but to enable writing multitask applications with ease.

Compatible with Python 2 and 3.

# Example

```python
from nr.concurrency import Job, as_completed
from requests import get
urls = ['https://google.com', 'https://github.com', 'https://readthedocs.org']
for job in as_completed(Job(target=(lambda: get(x)), start=True) for x in urls):
  print(job.result)
```

# Members

main_thread (threading._MainThread): The main-thread object.
"""

import collections
import functools
import threading
import time
import traceback
import sys
from threading import current_thread

try:
  import queue
except ImportError:
  import Queue as queue


main_thread = next(t for t in threading.enumerate()
  if isinstance(t, threading._MainThread))

# Synchronizable API
# ============================================================================

class Synchronizable(object):
  """
  Base class that implements the #Synchronizable interface. Classes that
  inherit from this class can automatically be used with the #synchronized(),
  #wait(), #notify() and #notify_all() functions.

  # Attributes

  synchronizable_lock_type[static]: A type or function that returns lock
    object. Defaults to #threading.RLock.

  synchronizable_condition_type[static]: A type or function that accepts
    an instance of `synchronizable_lock_type` as its first argument and
    returns a new condition variable.

  synchronizable_lock: An instance of type `synchronizable_lock_type`.

  synchronizable_condition: An instance of type `synchronizable_condition_type`.
    The `synchronizable_lock` is passed as an argument to the constructor when
    the condition variable is created.
  """

  synchronizable_lock_type = staticmethod(threading.RLock)
  synchronizable_condition_type = staticmethod(threading.Condition)

  def __new__(cls, *args, **kwargs):
    instance = super(Synchronizable, cls).__new__(cls)
    instance.synchronizable_lock = cls.synchronizable_lock_type()
    instance.synchronizable_condition = cls.synchronizable_condition_type(instance.synchronizable_lock)
    return instance


def synchronized(obj):
  """
  This function has two purposes:

  1. Decorate a function that automatically synchronizes access to the object
     passed as the first argument (usually `self`, for member methods)
  2. Synchronize access to the object, used in a `with`-statement.

  Note that you can use #wait(), #notify() and #notify_all() only on
  synchronized objects.

  # Example
  ```python
  class Box(Synchronizable):
    def __init__(self):
      self.value = None
    @synchronized
    def get(self):
      return self.value
    @synchronized
    def set(self, value):
      self.value = value

  box = Box()
  box.set('foobar')
  with synchronized(box):
    box.value = 'taz\'dingo'
  print(box.get())
  ```

  # Arguments
  obj (Synchronizable, function): The object to synchronize access to, or a
    function to decorate.

  # Returns
  1. The decorated function.
  2. The value of `obj.synchronizable_condition`, which should implement the
     context-manager interface (to be used in a `with`-statement).
  """

  if hasattr(obj, 'synchronizable_condition'):
    return obj.synchronizable_condition
  elif callable(obj):
    @functools.wraps(obj)
    def wrapper(self, *args, **kwargs):
      with self.synchronizable_condition:
        return obj(self, *args, **kwargs)
    return wrapper
  else:
    raise TypeError('expected Synchronizable instance or callable to decorate')


def wait(obj, timeout=None):
  """
  Wait until *obj* gets notified with #notify() or #notify_all(). If a timeout
  is specified, the function can return without the object being notified if
  the time runs out.

  Note that you can only use this function on #synchronized() objects.

  # Arguments
  obj (Synchronizable): An object that can be synchronized.
  timeout (number, None): The number of seconds to wait for the object to get
    notified before returning. If not value or the value #None is specified,
    the function will wait indefinetily.
  """

  if timeout is None:
    return obj.synchronizable_condition.wait()
  else:
    return obj.synchronizable_condition.wait(timeout)

def notify(obj):
  """
  Notify *obj* so that a single thread that is waiting for the object with
  #wait() can continue. Note that you can only use this function on
  #synchronized() objects.

  # Arguments
  obj (Synchronizable): The object to notify.
  """

  return obj.synchronizable_condition.notify()


def notify_all(obj):
  """
  Like #notify(), but allow all waiting threads to continue.
  """

  return obj.synchronizable_condition.notify_all()


# Job API
# ============================================================================

class Job(Synchronizable):
  """
  This class represents a task (Python function) and its result. The result is
  stored in the #Job object and can be retrieved at any time, given that the
  job has finished successfully. Exceptions that ocurr inside the Python
  function that is invoked by the job can propagated to the caller that obtains
  the result of the job.

  # Job States

  A job can only be in one state at a time. Depending on the state, fetching
  the result of the job will either raise an #InvalidState exception, a
  #Cancelled exception, any other exception that ocurred in the Python function
  that was called by the job, or actually return the result.

  Possible states are:

  - `Job.PENDING`: The job is waiting to be started.
  - `Job.RUNNING`: The job is currently running.
  - `Job.ERROR`: The execution of the job resulted in an exception.
  - `Job.SUCCESS`: The job finished successfully and the result can be obtained.
  - `Job.CANCELLED`: The job was cancelled and finished. Note that this state
    entered after the #Job.cancelled flag is set.

  # Events

  For every job, one or more callbacks can be registered which is invoked every
  time the job transitions into a new state. See #Job.add_listener() and
  #Job.listen().

  # Parameters

  task (callable): A callable accepting #Job object as argument that actually
    performs the task and returns the result. If you want to pass a callable
    that takes no arguments, pass it via the `target` parameter.
  target (callable): Just as the `task` parameter, but this time the function
    does not accept any arguments. Note that the two parameters can not be
    specified at the same time. Doing so will result in a #TypeError.
  name (any):
  start (bool): #True if the job should be started in a separate thread
    immediately. Defaults to #False.
  data (any):
  print_exc (bool):

  # Attributes

  name (any): An identifier for the Job. Defaults to #None. This member is
    useful for debugging concurrent applications by giving Jobs a unique name.

  data (any): This member can be filled with an arbitrary Python object.
    Useful to store context information that is needed when the Job finished.
    Note that access to this member, if not already garuanteed to be exclusive,
    must be #synchronized().

  print_exc (bool): Whether to print the traceback of exceptions ocurring in
    the #Job.run() or #Job.target or not. Defaults to #True.
  """

  PENDING = 'pending'
  RUNNING = 'running'
  ERROR = 'error'
  SUCCESS = 'success'
  CANCELLED = 'cancelled'

  _Listener = collections.namedtuple('_Listener', 'callback once')
  ExceptionInfo = collections.namedtuple('ExceptionInfo', 'type value tb')

  class Timeout(Exception):
    " Raised when a timeout occurred in #Job.wait(). "

  class Cancelled(Exception):
    " Raised when the Job was cancelled in #Job.wait() or #Job.result. "

  class InvalidState(Exception):
    """
    Raised when the Job is in a state that is not supported by the requested
    operation (eg. reading the result while the job is still running).
    """

  def __init__(self, task=None, target=None, name=None, start=False, data=None, print_exc=True):
    super(Job, self).__init__()
    if target is not None:
      if task is not None:
        raise TypeError('either task or target parameter must be specified, not both')
      task = lambda j: target()
    self.__target = task
    self.__thread = None
    self.__state = Job.PENDING
    self.__cancelled = False
    self.__result = None
    self.__exception = None
    self.__listeners = {None: [], Job.SUCCESS: [], Job.ERROR: [], Job.CANCELLED: []}
    self.__event_set = set()
    self.name = name
    self.data = data
    self.print_exc = print_exc
    if start: self.start()

  def __repr__(self):
    if self.name:
      name = self.name
    elif hasattr(self.__target, '__name__'):
      name = self.__target.__name__
    elif hasattr(self, 'name'):
      name = self.name
      if callable(name):
        name = name()
    else:
      name = None

    with synchronized(self):
      state = self.__state
      cancelled = self.__cancelled

    result = '<cancelled Job' if (cancelled and state != Job.CANCELLED) else '<Job'
    result += ' {0!r} at 0x{1:x}, state: {2}>'.format(name, id(self), state)
    return result

  @property
  @synchronized
  def state(self):
    " The job's state, one of #PENDING, #RUNNING, #ERROR, #SUCCESS or #CANCELLED. "

    return self.__state

  @property
  @synchronized
  def result(self):
    """
    The result of the jobs execution. Accessing this property while the job is
    pending or running will raise #InvalidState. If an exception occured during
    the jobs execution, it will be raised.

    # Raises
    InvalidState: If the job is not in state #FINISHED.
    Cancelled: If the job was cancelled.
    any: If an exception ocurred during the job's execution.
    """

    if self.__cancelled:
      raise Job.Cancelled
    elif self.__state in (Job.PENDING, Job.RUNNING):
      raise Job.InvalidState('job is {0}'.format(self.__state))
    elif self.__state == Job.ERROR:
      reraise(*self.__exception)
    elif self.__state == Job.SUCCESS:
      return self.__result
    else:
      raise RuntimeError('invalid job state {0!r}'.format(self.__state))

  @property
  @synchronized
  def exception(self):
    """
    The exception that occured while the job executed. The value is #None if
    no exception occurred.

    # Raises
    InvalidState: If the job is #PENDING or #RUNNING.
    """

    if self.__state in (Job.PENDING, Job.RUNNING):
      raise self.InvalidState('job is {0}'.format(self.__state))
    elif self.__state == Job.ERROR:
      assert self.__exception is not None
      return self.__exception
    elif self.__state in (Job.RUNNING, Job.SUCCESS, Job.CANCELLED):
      assert self.__exception is None
      return None
    else:
      raise RuntimeError('invalid job state {0!r}'.format(self.__state))

  @property
  @synchronized
  def pending(self):
    " True if the job is #PENDING. "

    return self.__state == Job.PENDING

  @property
  @synchronized
  def running(self):
    " True if the job is #RUNNING. "

    return self.__state == Job.RUNNING

  @property
  @synchronized
  def finished(self):
    """
    True if the job run and finished. There is no difference if the job
    finished successfully or errored.
    """

    return self.__state in (Job.ERROR, Job.SUCCESS, Job.CANCELLED)

  @property
  @synchronized
  def cancelled(self):
    """
    This property indicates if the job was cancelled. Note that with this flag
    set, the job can still be in any state (eg. a pending job can also be
    cancelled, starting it will simply not run the job).
    """

    return self.__cancelled

  @synchronized
  def get(self, default=None):
    """
    Get the result of the Job, or return *default* if the job is not finished
    or errored. This function will never explicitly raise an exception. Note
    that the *default* value is also returned if the job was cancelled.

    # Arguments
    default (any): The value to return when the result can not be obtained.
    """

    if not self.__cancelled and self.__state == Job.SUCCESS:
      return self.__result
    else:
      return default

  def cancel(self):
    """
    Cancels the job. Functions should check the #Job.cancelled flag from time
    to time to be able to abort pre-emptively if the job was cancelled instead
    of running forever.
    """

    with synchronized(self):
      cancelled = self.__cancelled
      if not cancelled:
        self.__cancelled = True
        notify_all(self)

    if not cancelled:
      self._trigger_event(Job.CANCELLED)

  @synchronized
  def _trigger_event(self, event):
    """
    Private. Triggers and event and removes all one-off listeners for that event.
    """

    if event is None or event not in self.__listeners:
      raise ValueError('invalid event type: {0!r}'.format(event))

    # Check the event has not already been triggered, then mark
    # the event as triggered.
    if event in self.__event_set:
      raise RuntimeError('event already triggered: {0!r}'.format(event))
    self.__event_set.add(event)
    listeners = self.__listeners[event] + self.__listeners[None]

    # Remove one-off listeners.
    self.__listeners[event][:] = (l for l in self.__listeners[event] if not l.once)
    self.__listeners[None][:] = (l for l in self.__listeners[None] if not l.once)

    for listener in listeners:
      # XXX: What to do on exceptions? Catch and make sure all listeners
      # run through? What to do with the exception(s) then?
      listener.callback(self, event)

  def add_listener(self, event, callback, once=False):
    """
    Register a *callback* for the specified *event*. The function will be
    called with the #Job as its first argument. If *once* is #True, the
    listener will be removed after it has been invoked once or when the
    job is re-started.

    Note that if the event already ocurred, *callback* will be called
    immediately!

    # Arguments
    event (str): The name of an event, or None to register the callback to be
      called for any event.
    callback (callable): A function.
    once (bool): Whether the callback is valid only once.
    """

    if not callable(callback):
      raise TypeError('callback must be callable')
    if event not in self.__listeners:
      raise ValueError('invalid event type: {0!r}'.format(event))

    event_passed = False
    with synchronized(self):
      event_passed = (event in self.__event_set)
      if not (once and event_passed):
        self.__listeners[event].append(Job._Listener(callback, once))

    # If the event already happened, we'll invoke the callback
    # immediately to make up for what it missed.
    if event_passed:
      callback(self, event)

  def wait(self, timeout=None):
    """
    Waits for the job to finish and returns the result.

    # Arguments
    timeout (number, None): A number of seconds to wait for the result
      before raising a #Timeout exception.

    # Raises
    Timeout: If the timeout limit is exceeded.
    """

    start_t = time.time()
    with synchronized(self):
      while self.__state == Job.RUNNING and not self.__cancelled:
        if timeout is None:
          wait(self)
        else:
          time_passed = time.time() - start_t
          if time_passed > timeout:
            raise Job.Timeout
          wait(self, timeout - time_passed)
    return self.result

  def start(self, as_thread=True, daemon=False, __state_check=True):
    """
    Starts the job. If the job was run once before, resets it completely. Can
    not be used while the job is running (raises #InvalidState).

    # Arguments
    as_thread (bool): Start the job in a separate thread. This is #True by
      default. Classes like the #ThreadPool calls this function from its own
      thread and passes #False for this argument.
    daemon (bool): If a thread is created with *as_thread* set to #True,
      defines whether the thread is started as a daemon or not. Defaults to
      #False.

    # Returns
    Job: The job object itself.
    """

    if __state_check:
      # We need to manually manage the lock to be able to release it
      # pre-emptively when needed.
      with synchronized(self):
        if self.__cancelled and self.__state == Job.PENDING:
          # Cancelled in PENDING state. Do not run the target function at all.
          self.__state = Job.CANCELLED
          assert self.__exception is None
          assert self.__result is None
          self._trigger_event(Job.CANCELLED)
          return None

        if self.__state == Job.RUNNING:
          raise Job.InvalidState('job is already running')
        elif self.__state not in (Job.PENDING, Job.ERROR, Job.SUCCESS, Job.CANCELLED):
          raise RuntimeError('invalid job state {0!r}'.format(self.__state))

        # Reset the Job attributes.
        self.__state = Job.RUNNING
        self.__cancelled = False
        self.__result = None
        self.__exception = None
        self.__event_set.clear()
        self.__thread = None

        # Remove all listeners that have been registered with the "once" flag.
        for listeners in self.__listeners.values():
          listeners[:] = (l for l in listeners if not l.once)

    if as_thread:
      thread = threading.Thread(target=self.start, args=(False, False, False))
      thread.setDaemon(daemon)
      with synchronized(self):
        assert not self.__thread or not self.__thread.running
        self.__thread = thread
      thread.start()
      return self

    try:
      result = None
      exception = None
      try:
        result = self.run()
        state = Job.SUCCESS
      except Exception:  # XXX: Catch BaseException?
        if self.print_exc:
          traceback.print_exc()
        exception = Job.ExceptionInfo(*sys.exc_info())
        state = Job.ERROR

      with synchronized(self):
        cancelled = self.__cancelled
        self.__result = result
        self.__exception = exception
        self.__state = Job.CANCELLED if cancelled else state

      self._trigger_event(state)
    finally:
      with synchronized(self):
        notify_all(self)

    return self

  def run(self):
    """
    This method is the actual implementation of the job. By default, it calls
    the target function specified in the #Job constructor.
    """

    if self.__target is not None:
      return self.__target(self)
    raise NotImplementedError

  @staticmethod
  def factory(start_immediately=True):
    """
    This is a decorator function that creates new `Job`s with the wrapped
    function as the target.

    # Example
    ```python
    @Job.factory()
    def some_longish_function(job, seconds):
      time.sleep(seconds)
      return 42

    job = some_longish_function(2)
    print(job.wait())
    ```

    # Arguments
    start_immediately (bool): #True if the factory should call #Job.start()
      immediately, #False if it should return the job in pending state.
    """

    def decorator(func):
      def wrapper(*args, **kwargs):
        job = Job(task=lambda j: func(j, *args, **kwargs))
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
  [job.add_listener(Job.SUCCESS, callback, once=True) for job in jobs]
  [job.add_listener(Job.ERROR, callback, once=True) for job in jobs]

  while jobs:
    event.wait()
    event.clear()

    jobs, finished = split_list_by(jobs, lambda x: x.finished)
    for job in finished:
      yield job


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

  Timeout = Job.Timeout

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



class Empty(Exception):
  ''' Raised by `SynchronizedDeque.get()`. '''

class SynchronizedDeque(Synchronizable):
  ''' Thread-safe wrapper for the `collections.deque`. *New in 0.9.6*. '''

  Empty = Empty
  Timeout = Job.Timeout

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
