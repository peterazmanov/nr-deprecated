+++
description = "Type arguments support."
+++

## Example

```python
import nr.generic

class TypedList(nr.generic.Generic):

  __generic_args__ = ['T']

  def __init__(self):
    nr.generic.assert_initialized(self)
    self._data = []
  
  def append(self, item):
    if not isinstance(item, self.T):
      raise TypeError('expected {}'.format(self.T.__name__))
    self._data.append(item)
  
  # ...

IntList = TypedList[int]
```
