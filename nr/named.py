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

from .datastructures.ordereddict import OrderedDict
from . import compat


class _named_meta(type):
  """
  Metaclass for the #named class.
  """

  def __init__(self, name, bases, data):
    # Inherit the annotations of the base classes, in the correct order.
    annotations = getattr(self, '__annotations__', {})
    if isinstance(annotations, (list, tuple)):
      for i, item in enumerate(annotations):
        if len(item) == 3:
          setattr(self, item[0], item[2])
          item = item[:2]
          annotations[i] = item
      annotations = OrderedDict(annotations)
    new_annotations = OrderedDict()
    for base in bases:
      base_annotations = getattr(base, '__annotations__', {})
      if isinstance(base_annotations, (list, tuple)):
        base_annotations = OrderedDict(base_annotations)
      for key, value in base_annotations.items():
        if key not in annotations:
          new_annotations[key] = value
    new_annotations.update(annotations)
    self.__annotations__ = new_annotations
    super().__init__(name, bases, data)


class named(compat.with_metaclass(_named_meta)):
  """
  A base-class similar to #typing.NamedTuple, but mutable. Fields can be
  specified using Python 3.6 class-member annotations or by setting the
  `__annotations__` field to a list where each item is a member declaration
  that consists of two or three items where 1) is the name, 2) is the
  annotated value (type) and 3) is the default value for the field.
  """

  def __init__(self, *args, **kwargs):
    annotations = getattr(self, '__annotations__', {})
    if len(args) > len(annotations):
      raise TypeError('{}() expected {} positional arguments, got {}'
        .format(type(self).__name__, len(annotations), len(args)))
    if isinstance(annotations, (list, tuple)):
      annotations = OrderedDict(annoations)

    for arg, (key, ant) in zip(args, annotations.items()):
      setattr(self, key, arg)
      if key in kwargs:
        raise TypeError('{}() duplicate value for argument "{}"'
          .format(type(self).__name__, key))

    for key, ant in annotations.items():
      if key in kwargs:
        setattr(self, key, kwargs.pop(key))
      else:
        try:
          value = getattr(self, key)
        except AttributeError:
          raise TypeError('{}() missing argument "{}"'
            .format(type(self).__name__, key))
        if isinstance(value, named_initializer):
          setattr(self, key, value.func())

    for key in kwargs.keys():
      raise TypeError('{}() unexpected keyword argument "{}"'
        .format(type(self).__name__, key))

  def __repr__(self):
    members = ', '.join('{}={!r}'.format(k, getattr(self, k)) for k in self.__annotations__)
    return '{}({})'.format(type(self).__name__, members)

  def __iter__(self):
    for key in self.__annotations__:
      yield getattr(self, key)

  def asdict(self):
    return {k: getattr(self, k) for k in self.__annotations__}


class named_initializer:
  """
  Use this for the default value of annotated fields to wrap a function that
  will be called to retrieve the default value for the field. Works only with
  #named as the base class.
  """

  def __init__(self, func):
    self.func = func


initializer = named
