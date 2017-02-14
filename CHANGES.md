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
