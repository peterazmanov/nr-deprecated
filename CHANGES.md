### v2.0.0

* Update module structure
* Removed `nr.misc.cli` module
* Removed `nr.types.singleton` module

__nr.version__

* New semantic, a `.extension` indicates that it is higher than the
  version without the extension, a `-extension` indicates that it is lower.
* Add `+extension` as synonym for `.extension`
* Allow version number extensions without a separating character, behaving
  like a `+extension` or `.extension`

### v1.4.10

__nr.parse.strex__

- More fix to `Scanner.seek()` going backwards from current cursor position
- Add testcase for `Scanner.seek()`

### v1.4.9

__nr.parse.strex__

- Fix `Scanner.seek()` when going backwards

### v1.4.8

__nr.parse.strex__

- Change `Lexer` now supports multiple rules with the same name

### v1.4.7

__nr.py.bytecode__

- Fix `get_assigned_name()` now wirks with Python 3.6
- Add testcase for nested calls of `get_assigned_name()`

__nr.concurrency__

- Add `Job(dispose_inputs)` parameter
- Add `ThreadPool(dispose_inputs)` parameter

### v1.4.6

__nr.parse.concurrency__

- Change `Job.wait()` can now be called while Job is pending
- Change `ThreadPool.submit()` interface
- Change `ThreadPool` no longer starts immediately when created
- Change `ThreadPool.__enter__()` can not be used when the pool already started
- Add `Job(args, kwargs)` parameters
- Add `ThreadPool.start()` method
- Add `ThreadPool.submit_multiple()` method
- Add `JobCollection` class

### v1.4.5

__nr.parse.strex__

- Add `Token.string_repr`
- Change `Rule.tokenize()` can now return a tuple of `(value, string_repr)`

### v1.4.4

__nr.parse.strex__

- Add `Scanner.seek()` method
- Add `Scanner.getmatch()` method

### v1.4.3

__nr.parse.strex__

- Fix `Scanner.next()` returning the new character, not the scanner
- Fix invalid use of `Scanner.next_get()`

### v1.4.2

__nr.misc.archive__

- Add `extract(default_mode='755')` argument
- If no file mode is contained in the `external_attr` field of a file, this
  default mode is applied (that is, when the mode is `000`)

### v1.4.1

__nr.misc.archive__

- `extract()` now sets file permissions and modification time
- Add a very basic command-line interface

### v1.4.0

__nr.concurrency__

- Add `wait_for_condition()`
- Renamed events
- Change `Job.start()` now returns self
- Change `Synchronizable` members

__nr.parse.strex__

- Move `readline()` and `match()` functions to `Scanner` class
- Remove `Lexer(raise_invalid)` parameter and attribute (was unused)

__nr.tundras__

- New library added

__nr.misc.archive__

- Now Python 2 compatible
