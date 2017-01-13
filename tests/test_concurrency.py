# Copyright (c) 2017  Niklas Rosenstein
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

from nr.concurrency import *
from time import sleep
from nose.tools import *

# Test Synchronizable
# ============================================================================

def test_wait_for_condition():
  obj = Synchronizable()
  obj.value = 0
  cond = lambda obj: obj.value == 10

  @Job.factory()
  def increment(job, time_interval):
    while not job.cancelled:
      with synchronized(obj):
        obj.value += 1
        notify_all(obj)
      sleep(time_interval)

  job = increment(0.01)
  try:
    assert_equals(wait_for_condition(obj, cond), True)
  finally:
    job.cancel()
    obj.value = 0

  job = increment(0.05)
  try:
    assert_equals(wait_for_condition(obj, cond, 0.2), False)
    assert_equals(wait_for_condition(obj, cond, 0.5), True)
  finally:
    job.cancel()


# Test Job
# ============================================================================

def worker(s, v):
  sleep(s)
  return v


def raiser(exc):
  raise exc


def worker_for_cancel(job):
  while not job.cancelled:
    sleep(0.05)


class CustomException(Exception): pass


def test_simple_jobs():
  job1 = Job(target=lambda: worker(0.05, 42)).start()
  job2 = Job(target=lambda: worker(0.10, 99)).start()
  assert_equals(job1.wait(), 42)
  assert_equals(job2.wait(), 99)


def test_forward_exception():
  job = Job(target=lambda: raiser(CustomException), print_exc=False).start()
  with assert_raises(CustomException):
    job.wait()


def test_cancel():
  job = Job(task=worker_for_cancel).start()
  sleep(0.1)
  job.cancel()
  with assert_raises(Job.Cancelled):
    job.result


def test_as_completed():
  jobs = [Job(target=lambda: worker(0.15, 'job1')).start(),
          Job(target=lambda: worker(0.05, 'job2')).start(),
          Job(target=lambda: worker(0.10, 'job3')).start()]
  results = []
  for job in as_completed(jobs):
    results.append(job.result)
  # We'll assume that the time a job sleeps is enough to make up for any
  # OS schedule interference with the completion order.
  assert_equals(results, ['job2', 'job3', 'job1'])
