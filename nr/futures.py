# The MIT License (MIT)
#
# Copyright (c) 2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import print_function
from nr.compat import reraise
import collections
import functools
import time
import threading
import traceback
import sys


class Future(object):
  """
  This class represents a task that can be executed in a separate thread.
  The result can then be obtained via the :meth:`result` or :meth:`get`
  method.

  The way exceptions are handled inside the future depends on the policy
  the is defined when the future is created. When you never intend to
  explicitly retrieve the result of the future, the exception will be
  immediately printed using :func:`traceback.print_exc()`. This is the
  default behaviour.

  If you intend to retrieve the result of the future at some point, the
  exception will be reraised when you call :meth:`result`. If the future is
  garbage collected before the exception was retrieved and reraised at least
  once, it will be printed before the future gets collected.

  Before you start a future, you must bind a worker function to it either
  by passing a callable as the first argument or using the :meth:`bind`
  method.

  .. code-block:: python

    f = Future(lambda: worker(arg1, arg2='Foo'))
    f = Future().bind(worker, arg1, arg2='Foo')

  If you want to pass the future as an argument to the worker function,
  you need to temporarily assign the future to a variable. Passing the
  future to the worker function allows the worker to check the state of
  the future, most notably if it has been :meth:`cancelled`.

  .. code-block:: python

    f = Future(lambda: worker(f))
    f.start()

  Note that the worker function is deleted from the future after it has
  been run or cancelled. Future objects are not supposed to be reused.

  If you expect to collect the result of the future, pass :const:`True`
  to the *collect_result* parameter. If you do expect to collect the result
  but never do, the exception will be printed when the future is deleted.

  .. code-block:: python

    f = Future((lambda: 42 * gimme_that_error), True)
    f.start()
    del f
    # printed to console (not actually raised)
    # NameError: global name 'bar' is not defined

  :param worker: The worker function to be bound to the future. Can also
    be set with :meth:`bind()`. If this is a boolean value, the parameter
    takes on the semantics of *collect_result*.
  :param collect_result: Set to :const:`True` if you expect to collect the
    result of this future. Defaults to :const:`False`.
  """

  def __init__(self, worker=None, collect_result=False):
    if isinstance(worker, bool):
      worker = None
      collect_result = worker
    if worker is not None and not callable(worker):
      raise TypeError('worker must be callable')
    self._collect_result = collect_result
    self._worker = worker
    self._thread = None
    self._enqueued = False
    self._exc_info = None
    self._exc_retrieved = False
    self._lock = threading.Condition()
    self._running = False
    self._completed = False
    self._cancelled = False
    self._result = None
    self._done_callbacks = []

  def __repr__(self):
    with self._lock:
      if self._exc_info:
        status = 'error ({})'.format(self._exc_info[1])
      elif self._cancelled:
        status = 'cancelled'
      elif self._completed:
        status = 'completed'
      elif self._running:
        status = 'running'
      elif self._enqueued:
        status = 'enqueued'
      else:
        status = 'pending'
      return '<Future {}>'.format(status)

  def bind(self, __fun, *args, **kwargs):
    """
    Bind a worker function to the future. This worker function will be
    executed when the future is executed.
    """

    with self._lock:
      if self._running or self._completed or self._cancelled:
        raise RuntimeError('Future object can not be reused')
      if self._worker:
        raise RuntimeError('Future object is already bound')
      self._worker = functools.partial(__fun, *args, **kwargs)
    return self

  def add_done_callback(self, fun):
    """
    Adds the callback *fun* to the future so that it be invoked when the
    future completed. The future completes either when it has been completed
    after being started with the :meth:`start` method (independent of whether
    an error occurs or not) or when either :meth:`set_result` or
    :meth:`set_exception` is called.

    If the future is already complete, *fun* will be invoked directly.

    The function *fun* must accept the future as its sole argument.
    """

    with self._lock:
      if self._completed:
        fun()
      else:
        self._done_callbacks.append(fun)

  def enqueue(self):
    """
    Mark the future as being enqueued in some kind of executor for futures.
    Calling :meth:`start()` with the *as_thread* parameter as :const:`True`
    will raise a :class:`RuntimeError` after this method has been called.

    This method will also validate the state of the future.
    """

    with self._lock:
      if self._enqueued:
        raise RuntimeError('Future object is already enqueued')
      if self._running:
        raise RuntimeError('Future object is already running')
      if self._completed:
        raise RuntimeError('Future object can not be restarted')
      if not self._worker:
        raise RuntimeError('Future object is not bound')
      self._enqueued = True

  def start(self, as_thread=True):
    """
    Execute the future in a new thread or in the current thread as specified
    by the *as_thread* parameter.

    :param as_thread: Execute the future in a new, separate thread. If this
      is set to :const:`False`, the future will be executed in the calling
      thread.
    """

    with self._lock:
      if as_thread:
        self.enqueue()  # Validate future state
      if self._cancelled:
        return

      self._running = True
      if as_thread:
        self._thread = threading.Thread(target=self._run)
        self._thread.start()
        return self

    self._run()

  def _run(self):
    result = None
    exc_info = None
    try:
      result = self._worker()
    except:
      exc_info = sys.exc_info()
      if not self._collect_result:
        # The result is not expected to be collected, thus the exception
        # would be swallowed. We print it immediately.
        traceback.print_exc()
    with self._lock:
      self._worker = None
      self._result = result
      self._exc_info = exc_info
      self._completed = True
      self._lock.notify_all()
      callbacks = self._prepare_done_callbacks()
    try:
      callbacks()
    except:
      traceback.print_exc()

  # @requires_lock
  def _prepare_done_callbacks(self):
    callbacks, self._done_callbacks = self._done_callbacks, []
    def invoker():
      for callback in callbacks:
        try:
          callback(self)
        except:
          traceback.print_exc()
    return invoker

  def enqueued(self):
    """
    :return: :const:`True` if the future is enqueued, meaning that it is about
      to be or already being executed.
    """

    with self._lock:
      return self._enqueued

  def running(self):
    """
    :return: :const:`True` if the future is running, :const:`False` otherwise.
    """

    with self._lock:
      return self._running

  def done(self):
    """
    :return: :const:`True` if the future completed, :const:`False` otherwise.
    """

    with self._lock:
      return self._completed

  def cancelled(self):
    """
    Checks if the future has been cancelled.
    """

    with self._lock:
      return self._cancelled

  def result(self, timeout=None, do_raise=True):
    """
    Retrieve the result of the future, waiting for it to complete or at
    max *timeout* seconds.

    :param timeout: The number of maximum seconds to wait for the result.
    :param do_raise: Set to False to prevent any of the exceptions below
      to be raised and return :const:`None` instead.
    :raise Cancelled: If the future has been cancelled.
    :raise Timeout: If the *timeout* has been exceeded.
    :raise BaseException: Anything the worker has raised.
    :return: Whatever the worker bound to the future returned.
    """

    with self._lock:
      self.wait(timeout, do_raise=do_raise)
      if self._exc_info:
        if not do_raise:
          return None
        # Its more important to re-raise the exception from the worker.
        self._exc_retrieved = True
        reraise(*self._exc_info)
      if self._cancelled:
        if not do_raise:
          return None
        raise self.Cancelled()
      return self._result

  def exception(self, timeout=None, do_raise=True):
    """
    Returns the exception value by the future's worker or :const:`None`.

    :param timeout:
    :param do_raise:
    :param Cancelled:
    :param Timeout:
    :return: :const:`None` or an exception value.
    """

    with self._lock:
      self.wait(timeout, do_raise=do_raise)
      if not self._exc_info:
        return None
      self._exc_retrieved = True
      if self._cancelled:
        raise self.Cancelled()
      return self._exc_info[1]

  def exc_info(self, timeout=None, do_raise=True):
    """
    Returns the exception info tuple raised by the future's worker or
    :const:`None`.

    :param timeout:
    :param do_raise:
    :param Cancelled:
    :param Timeout:
    :return: :const:`None` or an exception info tuple.
    """

    with self._lock:
      self.wait(timeout, do_raise=do_raise)
      if not self._exc_info:
        return None
      self._exc_retrieved = True
      if self._cancelled:
        raise self.Cancelled()
      return self._exc_info

  def cancel(self, mark_completed_as_cancelled=False):
    """
    Cancel the future. If the future has not been started yet, it will never
    start running. If the future is already running, it will run until the
    worker function exists. The worker function can check if the future has
    been cancelled using the :meth:`cancelled` method.

    If the future has already been completed, it will not be marked as
    cancelled unless you set *mark_completed_as_cancelled* to :const:`True`.

    :param mark_completed_as_cancelled: If this is :const:`True` and the
      future has already completed, it will be marked as cancelled anyway.
    """

    with self._lock:
      if not self._completed or mark_completed_as_cancelled:
        self._cancelled = True
      callbacks = self._prepare_done_callbacks()
    callbacks()

  def set_result(self, result):
    """
    Allows you to set the result of the future without requiring the future
    to actually be executed. This can be used if the result is available
    before the future is run, allowing you to keep the future as the interface
    for retrieving the result data.

    :param result: The result of the future.
    :raise RuntimeError: If the future is already enqueued.
    """

    with self._lock:
      if self._enqueued:
        raise RuntimeError('can not set result of enqueued Future')
      self._result = result
      self._completed = True
      callbacks = self._prepare_done_callbacks()
    callbacks()

  def set_exception(self, exc_info):
    """
    This method allows you to set an exception in the future without requring
    that exception to be raised from the futures worker. This method can be
    called on an unbound future.

    :param exc_info: Either an exception info tuple or an exception value.
      In the latter case, the traceback will be automatically generated
      from the parent frame.
    :raise RuntimeError: If the future is already enqueued.
    """

    if not isinstance(exc_info, tuple):
      if not isinstance(exc_info, BaseException):
        raise TypeError('expected BaseException instance')
      try:
        # TODO: Filld the traceback so it appears as if the exception
        #       was actually raised by the caller? (Not sure if possible)
        raise exc_info
      except:
        exc_info = sys.exc_info()
        exc_info = (exc_info[0], exc_info[1], exc_info[2])

    with self._lock:
      if self._enqueued:
        raise RuntimeError('can not set exception of enqueued Future')
      self._exc_info = exc_info
      self._completed = True
      callbacks = self._prepare_done_callbacks()
    callbacks()

  def wait(self, timeout=None, do_raise=False):
    """
    Wait for the future to complete. If *timeout* is specified, it must be a
    floating point number representing the maximum number of seconds to wait.

    :param timeout: The maximum number of seconds to wait for the future
      to complete.
    :param do_raise: Raise :class:`Timeout` when a timeout occurred.
    :raise Timeout: If a timeout occurred and *do_raise* was True.
    :return: :const:`True` if the future completed, :const:`False` if a
      timeout occurred and *do_raise* was set to False.
    """

    if timeout is not None:
      timeout = float(timeout)
      start = time.clock()

    with self._lock:
      while not self._completed and not self._cancelled:
        if timeout is not None:
          time_left = timeout - (time.clock() - start)
        else:
          time_left = None
        if time_left is not None and time_left <= 0.0:
          if do_raise:
            raise self.Timeout()
          else:
            return False
        self._lock.wait(time_left)
    return True

  class Cancelled(Exception):
    pass

  class Timeout(Exception):
    pass


class ThreadPool(object):
  """
  Represents a pool of threads that can process futures.
  """

  def __init__(self, max_workers, daemon=True):
    self._workers = []
    self._daemon = daemon
    self._max_workers = max_workers
    self._num_running = 0
    self._queue = collections.deque()
    self._lock = threading.Condition()
    self._shutdown = False

  def __enter__(self):
    return self

  def __exit__(self, *a):
    self.shutdown()

  def enqueue(self, future):
    """
    Enqueue a future to be processed by one of the threads in the pool.
    The future must be bound to a worker and not have been started yet.
    """

    future.enqueue()
    with self._lock:
      self._queue.append(future)
      if self._num_running == len(self._workers):
        self._new_worker()
      self._lock.notify_all()

  def submit(self, __fun, *args, **kwargs):
    """
    Creates a new future and enqueues it. Returns the future.
    """

    future = Future().bind(__fun, *args, **kwargs)
    self.enqueue(future)
    return future

  def cancel(self):
    """
    Cancel all futures queued in the pool.
    """

    with self._lock:
      for future in self._queue:
        future.cancel()
      self._queue.clear()

  def shutdown(self, wait=True):
    """
    Shut down the pool. If *wait* is True, it will wait until all futures
    are completed.
    """

    with self._lock:
      self._shutdown = True
      self._lock.notify_all()
    if wait:
      for worker in self._workers:
        worker.join()

  def _new_worker(self):
    with self._lock:
      if len(self._workers) < self._max_workers:
        worker = self._Worker(self)
        worker.daemon = self._daemon
        self._workers.append(worker)
        worker.start()

  class _Worker(threading.Thread):

    def __init__(self, master):
      threading.Thread.__init__(self)
      self._master = master

    def run(self):
      while True:
        with self._master._lock:
          while not self._master._queue:
            if self._master._shutdown:
              return
            self._master._lock.wait()
          self._master._num_running += 1
          future = self._master._queue.popleft()
        try:
          future.start(as_thread=False)
        finally:
          with self._master._lock:
            self._master._num_running -= 1
