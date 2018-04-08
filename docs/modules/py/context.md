+++
description = "Some context handlers."
+++

## `SkippableContextManager`

This class implements a skippable context manager. When you create a subclass
and implement `__enter__()`, you can use the #skip() function from within to
skip the with context entirely.

__Example__

```python
import nr.py.context as context

class IfContext(context.SkippableContextManager):
  def __init__(self, cond):
    self.cond = cond
  def __enter__(self):
    if not self.cond:
      context.skip()
    return self

with IfContext(False):
  FooLalala.ThisIsNotBeingExecuted
```
