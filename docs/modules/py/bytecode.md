+++
description = "Some bytecode stuff."
+++

## `get_assigned_name()`

Checks the bytecode of *frame* to find the name of the variable a result is
being assigned to and returns that name. Returns the full left operand of the
assignment. Raises a #ValueError if the variable name could not be retrieved
from the bytecode (eg. if an unpack sequence is on the left side of the
assignment).

> **Known Limitations**:  The expression in the *frame* from which this
> function is called must be the first part of that expression. For
> example, `foo = [get_assigned_name(get_frame())] + [42]` works,
> but `foo = [42, get_assigned_name(get_frame())]` does not!

```python
>>> var = get_assigned_name(sys._getframe())
>>> assert var == 'var'
```

__Available in Python 3.4, 3.5__
