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

class ObjectFromMapping(object):
  """
  This class wraps a dictionary and exposes its values as members.
  """

  def __init__(self, mapping, name=None):
    self.__mapping = mapping
    self.__name = name

  def __getattribute__(self, key):
    if key.startswith('_ObjectFromMapping__'):
      return super(ObjectFromMapping, self).__getattribute__(key)
    try:
      return self.__mapping[key]
    except KeyError:
      raise AttributeError(key)

  def __setattr__(self, key, value):
    if key.startswith('_ObjectFromMapping__'):
      super(ObjectFromMapping, self).__setattr__(key, value)
    else:
      self.__mapping[key] = value

  def __delattr__(self, key):
    if key.startswith('_ObjectFromMapping__'):
      super(ObjectFromMapping, self).__delattr__(key)
    else:
      del self.__mapping[key]

  def __dir__(self):
    return sorted(self.__mapping.keys())

  def __repr__(self):
    if self.__name:
      return '<ObjectFromMapping name={!r}>'.format(self.__name)
    else:
      return '<ObjectFromMapping {!r}>'.format(self.__mapping)
