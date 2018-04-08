+++
description = "Class-layout specification (lile mutable namedtuples)."
+++

## Example (Python 3.6+)

```python
import nr.named

class Person(nr.named.named):
  name: str
  age: int = -1
  city: str = ""

print(Person("John", city="Manchester"))  # Person(name='John', age=-1, city='Manchester')
```

## Example (Python <3.6)

```python
import nr.named

class Person(nr.named.named):
  # Will be automatically converted to an OrderedDict.
  __annotations__ = [
    ('name', str),
    ('age', int, -1),
    ('city', str, "")
  ]
```
