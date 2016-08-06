:mod:`nr.utils.concurrency` --- Pure simplicity for concurrent applications
===========================================================================

.. module:: nr.utils.concurrency
  :synopsis: Pure simplicity for concurrent applications

The :mod:`~nr.utils.concurrency` module provides an easy to use toolkit
for developing concurrent applications.

Interacting with Synchronizables
--------------------------------

.. function:: synchronized(obj)

  Synchronizes access to the :class:`Synchronizable` *obj*. If *obj* is not
  a Synchronizable but a callable object, this function acts as a decorator
  and returns *obj* wrapped in a callable object that synchronizes access
  to the object passed as the first parameter.

  .. code:: python

    class MyData(Synchronizable):

      @synchronized
      def some_method(self, *args):
        # ...

    with synchronized(some_object):
      some_object.do_stuff()

.. function:: notify(obj)

  Notifies a thread waiting for *obj* to wake up.

.. function:: notify_all(obj)

  Notifies all threads waiting for *obj* to wake up.

.. function:: wait(obj, timeout=None)

  Wait for *obj* until :func:`notify` or :func:`notify_all` is called.

Synchronizable Class
--------------------

The Synchronizable is a base class for objects that can be shared among
multiple threads and provides a condition variable with each instance that
is created of the class.

.. autoclass:: Synchronizable

.. staticmethod:: Synchronizable.lock_type

  Returns a new synchronization primitive. The default implementation returns
  a :class:`threading.RLock`.

.. staticmethod:: Synchronizable.condition_type(lock)

  Returns a new condition variable. The default implementation returns a
  :class:`threading.Condition`.

Job Class
---------

.. autoclass:: Job

.. autofunction:: as_completed

ThreadPool Class
----------------

.. autoclass:: ThreadPool

EventQueue Class
----------------

.. autoclass:: EventQueue

SynchronizedDeque Class
-----------------------

.. autoclass:: SynchronizedDeque

Clock Class
-----------

.. autoclass:: Clock

Exceptions
----------

.. autoclass:: InvalidStateError
.. autoclass:: Cancelled
.. autoclass:: Timeout
.. autoclass:: Empty
