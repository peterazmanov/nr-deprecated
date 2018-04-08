+++
description = "Some Python metaclasses."
+++

## `InlineMetaclass`

A metaclass that allows you to implement metaclass creation and initialization
without a separate metaclass.

__Example__

```python
class MyClass(metaclass=InlineMetaclass):
  def __metanew__(meta, name, bases, dict):
    # Do the stuff you would usually do in your metaclass.__new__()
    return super(InlineMetaclass, meta).__new__(meta, name, bases, dict)
  def __metainit__(cls, name, bases, dict):
    # Do the stuff you would usually do in your metaclass.__init__()
    pass
```
