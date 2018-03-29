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

from .. import compat
from ..stream import stream

try: from collections import OrderedDict
except ImportError: from ._ordereddict import OrderedDict


class MappingFromObject(object):
  """
  This class wraps an object and exposes its members as mapping.
  """

  def __new__(cls, obj):
    if isinstance(obj, ObjectFromMapping):
      return obj._ObjectFromMapping__mapping
    return super(MappingFromObject, cls).__new__(cls)

  def __init__(self, obj):
    self.__obj = obj

  def __repr__(self):
    return 'MappingFromObject({!r})'.format(self.__obj)

  def __iter__(self):
    return self.keys()

  def __len__(self):
    return len(dir(self.__obj))

  def __contains__(self, key):
    return hasattr(self.__obj, key)

  def __getitem__(self, key):
    try:
      return getattr(self.__obj, key)
    except AttributeError:
      raise KeyError(key)

  def __setitem__(self, key, value):
    setattr(self.__obj, key, value)

  def __delitem__(self, key):
    delattr(self.__obj, key)

  def keys(self):
    return iter(dir(self.__obj))

  def values(self):
    return (getattr(self.__obj, k) for k in dir(self.__obj))

  def items(self):
    return ((k, getattr(self.__obj, k)) for k in dir(self.__obj))

  def get(self, key, default=None):
    return getattr(self.__obj, key, default)

  def setdefault(self, key, value):
    try:
      return getattr(self.__obj, key)
    except AttributeError:
      setattr(self.__obj, key, value)
      return value


class ObjectFromMapping(object):
  """
  This class wraps a dictionary and exposes its values as members.
  """

  def __new__(cls, mapping, name=None):
    if isinstance(mapping, MappingFromObject):
      return mapping._MappingFromObject__obj
    return super(ObjectFromMapping, cls).__new__(cls)

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


class ChainDict(object):
  """
  A dictionary that wraps a list of dictionaries. The dictionaries passed
  into the #ChainDict will not be mutated. Setting and deleting values will
  happen on the first dictionary passed.
  """

  def __init__(self, *dicts):
    if not dicts:
      raise ValueError('need at least one argument')
    self._major = dicts[0]
    self._dicts = list(dicts)
    self._deleted = set()
    self._in_repr = False

  def __contains__(self, key):
    if key not in self._deleted:
      for d in self._dicts:
        if key in d:
          return True
    return False

  def __getitem__(self, key):
    if key not in self._deleted:
      for d in self._dicts:
        try: return d[key]
        except KeyError: pass
    raise KeyError(key)

  def __setitem__(self, key, value):
    self._major[key] = value
    self._deleted.discard(key)

  def __delitem__(self, key):
    if key not in self:
      raise KeyError(key)
    self._major.pop(key, None)
    self._deleted.add(key)

  def __iter__(self):
    return compat.iterkeys(self)

  def __len__(self):
    return stream.count(self.keys())

  def __repr__(self):
    if self._in_repr:
      return 'ChainDict(...)'
    else:
      self._in_repr = True
      try:
        return 'ChainDict({})'.format(dict(compat.iteritems(self)))
      finally:
        self._in_repr = False

  def __eq__(self, other):
    return dict(self.items()) == other

  def __ne__(self, other):
    return not (self == other)

  def pop(self, key, default=NotImplemented):
    if key not in self:
      if default is NotImplemented:
        raise KeyError(key)
      return default
    self._major.pop(key, None)
    self._deleted.add(key)

  def popitem(self):
    if self._major:
      key, value = self._major.popitem()
      self._deleted.add(key)
      return key, value
    for d in self._dicts:
      for key in compat.iterkeys(d):
        if key not in self._deleted:
          self._deleted.add(key)
          return key, d[key]
    raise KeyError('popitem(): dictionary is empty')

  def clear(self):
    self._major.clear()
    self._deleted.update(compat.iterkeys(self))

  def copy(self):
    return type(self)(*self._dicts[1:])

  def setdefault(self, key, value=None):
    try:
      return self[key]
    except KeyError:
      self[key] = value
      return value

  def update(self, E, *F):
    if compat.can_iteritems(E):
      for k, v in compat.iteritems(E):
        self[k] = v
    elif compat.can_iterkeys(E):
      for k in compat.iterkeys(E):
        self[k] = E[k]
    else:
      for k, v in E:
        self[k] = v
    for Fv in F:
      for k, v in compat.iteritems(Fv):
        self[k] = v

  def keys(self):
    seen = set()
    for d in self._dicts:
      for key in compat.iterkeys(d):
        if key not in seen and key not in self._deleted:
          yield key
          seen.add(key)

  def values(self):
    seen = set()
    for d in self._dicts:
      for key, value in compat.iteritems(d):
        if key not in seen and key not in self._deleted:
          yield value
          seen.add(key)

  def items(self):
    seen = set()
    for d in self._dicts:
      for key, value in compat.iteritems(d):
        if key not in seen and key not in self._deleted:
          yield key, value
          seen.add(key)

  if compat.PY2:
    iterkeys = keys
    keys = lambda self: list(self.iterkeys())
    itervalues = values
    values = lambda self: list(self.itervalues())
    iteritems = items
    items = lambda self: list(self.iteritems())

