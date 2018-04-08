+++
description = "Python 2 compatible enumerations."
+++

## Examples

```python
import nr.enum

class Color(nr.enum.Enumeration):
  red = 0
  green = 1
  blue = 2

print(Color.red)  # <Color: red>
print(Color(0) is Color.red)  # True
print(list(Color))  # [<Color: red>, <Color: green>, <Color: blue>]
```
