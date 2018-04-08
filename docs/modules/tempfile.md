+++
description = "Sane tempfile class."
+++

With sane, I mean that you can close the file inside the context-manager
without deleting it. Only exiting the context manager will actually delete
the file.

```python
from nr.tempfile import tempfile

with tempfile(suffix='.c', text=True) as fp:
  fp.write('#include <stdio.h>\nint main() {}\n')
  fp.close()
  try_compile(fp.name)
```
