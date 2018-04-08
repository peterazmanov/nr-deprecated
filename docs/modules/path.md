+++
description = "Altenrative os.path interface with additional functionality."
+++

## Requirements

* [glob2](https://pypi.python.org/pypi/glob2) (optional, required for
  `nr.path.glob()`)

## Features

* Shortens functions like `abspath()` and `normpath()` to `abs()` and `norm()`
* Suffix operations (`setsuffix()`, `getsuffix()`, `rmvsuffix()`)
* Recursive glob with exclusion support (`glob()`, requires `glob2` module)
* Unix-style file permission handling (`chmod()`, `chmod_update()`, `chmod_repr()`)
* `makedirs()` does not error when directory already exists
