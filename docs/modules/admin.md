+++
description = "Run a command with elevated privileges (Windows/Posix)."
+++

This module implements running a system command with elevated privileges.
The new command *always* inherits the parent processes' environment.

## Example

```python
import nr.admin
import sys

if not nr.admin.is_admin():
  sys.exit(nr.admin.run_as_admin([sys.executable, __file__]))

assert nr.admin.is_admin()
```

## Implementation Details

* Windows: Uses `ShellExecuteEx()` and creates a temporary data directory
  that is used to transmit the command, working directory, environment
  variables and the process output to the calling non-elevated process.
* Posix: Uses `sudo -E`.

## Acknowledgements

* Many thanks to all answers from the StackOverflow question
  [How to run python script with elevated privilege on windows](https://stackoverflow.com/q/19672352/791713).
