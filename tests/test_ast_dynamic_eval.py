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

import textwrap
from nose.tools import *
from nr.ast.dynamic_eval import dynamic_exec, dynamic_eval


def test_dynamic_exec():
  assignments = {}
  assignments['assignments'] = lambda: assignments
  def resolve(x):
    try:
      return assignments[x]
    except KeyError:
      raise NameError(x)
  def assign(x, v):
    assignments[x] = v

  code = textwrap.dedent('''
    from nose.tools import *
    import os
    a, b = 0, 0
    def main():
      global a
      a = 42
      b = 99
      class Foo:
        a = 9999
        b = 9999
      print("Hello, World from", os.getcwd(), 'a, b', (a, b))
      assert_equals(a, 42)
      assert_equals(b, 99)
      assert_equals(assignments()['a'], 42)
      assert_equals(assignments()['b'], 0)
    main()
    assert_equals(a, 42)
    assert_equals(b, 0)
  ''')

  dynamic_exec(code, resolve, assign)

  for key in ('os', 'a', 'b', 'main'):
    assert key in assignments

  assert_equals(assignments['a'], 42)
  assert_equals(assignments['b'], 0)
