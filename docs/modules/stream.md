+++
description = "Chained stream processing."
+++

Provides a `stream` class that wraps an iterator and supports a number of
methods to further wrap and process it. Many methods can be used as both
instance and static methods.

__Example__

```python
from nr.stream import stream

for friend in stream(persons).attr('iter_friends').call().concat().unique():
  print(friend)
```

## `stream`

### `__getitem__(slice)`

### `call(iterable, *a, **kw)`

### `map(iterable, func, *a, **kw)`

### `filter(iterable, cond, *a, **kw)`

### `unique(iterable, key=None)`

### `chunks(iterable, n, fill=None)`

### `concat(iterables)`

### `chain(*iterables)`

### `attr(iterable, attr_name)`

### `item(iterable, key)`

### `of_type(iterable, types)`

### `partition(iterable, pred)`

### `dropwhile(iterable, pred)`

### `takewhile(iterable, pred)`

### `groupby(iterable, key=None)`

### `slice(iterable, *args, **kwargs)`

### `count(iterable)`

### `first(self)`
