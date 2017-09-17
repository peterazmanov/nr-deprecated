# Copyright (c) 2016  Niklas Rosenstein
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

import dis
import sys

from nose.tools import *
from sys import _getframe
from nr.py.bytecode import get_assigned_name, opstackd

if sys.version_info[0] == 3:
  py3only = istest
else:
  print('note: skipping tests for nr.py.bytecode on Python {}'.format(sys.version[:3]))
  py3only = nottest

@py3only
def test_opstackd_integrity():
  """
  Test if all keys in `magic.opstackd` are valid opcodes.
  """

  for key in opstackd:
    assert_in(key, dis.opname)

@py3only
def test_get_assigned_name_simple():
  """
  Test `magic.get_assigned_name()` in various use cases.
  """

  obj = type('', (), {})

  foo = get_assigned_name(_getframe())
  assert_equals("foo", foo)

  spam = [get_assigned_name(_getframe())] + ["bar"]
  assert_equals("spam", spam[0])

  obj.eggs = (lambda: get_assigned_name(_getframe(1)))()
  assert_equals("eggs", obj.eggs)

  with assert_raises(ValueError):
    get_assigned_name(_getframe())

  with assert_raises(ValueError):
    # get_assigned_name() branch must be first part of the expression.
    spam = [42] + [get_assigned_name(_getframe())] + ["bar"]
    assert "spam" == spam[0]

@py3only
def test_get_assigned_name_complex():

  def target1(inputs):
    return (inputs, get_assigned_name(_getframe(1)))

  def target2(name=None):
    if not name:
      try:
        return get_assigned_name(_getframe(1))
      except ValueError:
        return 'target2-default'

  mytarget = target1(
    inputs = [target2()]
  )
  assert_equals(mytarget[1], 'mytarget')
  assert_equals(mytarget[0][0], 'target2-default')
