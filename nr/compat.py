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

import sys

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
if not (PY2 or PY3):
  raise EnvironmentError('neither Python 2 or Python 3??')


def with_metaclass(metaclass):
  return metaclass('{}Temp'.format(metaclass.__name__), (object,), {})


if PY2:
  import __builtin__ as builtins

  def iteritems(d):
    return d.iteritems()

  def iterkeys(d):
    return d.iterkeys()

  def itervalues(d):
    return d.itervalues()

  def can_iteritems(d):
    return hasattr(d, 'iteritems')

  def can_iterkeys(d):
    return hasattr(d, 'iterkeys')

  def can_itervalues(d):
    return hasattr(d, 'itervalues')

  def exec_(code, globals=None, locals=None):
    if globals is None:
      frame = sys._getframe(1)
      globals = frame.f_globals
      if locals is None:
        locals = frame.f_locals
      del frame
    elif locals is None:
      locals = globals
    exec("""exec code in globals, locals""")

  range = xrange

  string_types = (str, unicode)
  text_type = unicode
  binary_type = str
  integer_types = (int, long)

else:
  import builtins

  def iteritems(d):
    return d.items()

  def iterkeys(d):
    return d.keys()

  def itervalues(d):
    return d.values()

  def can_iteritems(d):
    return hasattr(d, 'items')

  def can_iterkeys(d):
    return hasattr(d, 'keys')

  def can_itervalues(d):
    return hasattr(d, 'valyes')

  exec_ = getattr(builtins, 'exec')
  range = range

  string_types = (str,)
  text_type = str
  binary_type = bytes
  integer_types = (int,)
