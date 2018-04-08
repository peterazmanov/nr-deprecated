## `nr` &ndash; Compound utility library and command-line tools for Python 2/3

This library contains a variety of Python programming utilities that didn't
make it into separate modules. Additionally, this library comes with a bunch
of command-line tools.

Note that most components can be used independently from each other, and some
components may need additional dependencies. These additional dependencies are
currently not automatically installed when install `nr`.

### Components

* `nr.admin` &ndash; Run a command with elevated privileges on Windows and
  Posix systems.
* `nr.archive` &ndash; Archive handling abstraction.
* `nr.ast` &ndash; Tools to work with the Python AST.
  * `nr.ast.dynamic_eval` &ndash; Allows you to execute Python code with hooks
    for when a global variable is accessed or assigned.
* `nr.compat` &ndash; Simple Python 2/3 compatibility layer.
* `nr.concurrency` &ndash; Job scheduling and threaded event processing.
* `nr.datastructures` &ndash; Some data structures, including an `OrderedDict`
  for Python 2.6 (`from nr.datastructures.ordereddict import OrderedDict`).
* `nr.decorators` &ndash; Some Python function decorators.
* `nr.enum` &ndash; Python 2/3 compatible enumeration class.
* `nr.generic` &ndash; Python generic metaclass (type arguments).
* `nr.gitignore` &ndash; Parser and evaluator for `.gitignore` files.
* `nr.named` &ndash; Mutable namedtuples declarables as classes using
  `__annotations__` or the Python3.6+ class-level annotations syntax.
* `nr.path` &ndash; Alternative interface to `os.path` and some additional
  functions (requires `glob2` if you want to use the `nr.path.glob()` function).
* `nr.py.blob` &ndash; Convert Python source code into a base64 encoded blob.
* `nr.py.bytecode` &ndash; Helpers for working with Python bytecode.
* `nr.py.context` &ndash; Python context manager tools.
* `nr.py.meta` &ndash; Python metaclasses.
* `nr.recordclass` &ndash; Mutable namedtuples with support for default args.
* `nr.stream` &ndash; Provides a class for chained stream processing.
* `nr.strex` &ndash; String scanning and lexing facilities.
* `nr.tempfile` &ndash; A better temporary file and directory context manager.
* `nr.tools` &ndash; This package contains only command-line utilities.
* `nr.version` &ndash; Semantic version parser and evaluator.

### Command-line

* `nr archive` &ndash; Command-line of the `nr.archive` module
* `nr grablicense` &ndash; Print text for the specified license, optionally
  formatted properly for the specified language's comment syntax.
* `nr jiratime` &ndash; Sum up work times for a user in JIRA.
* `nr py.blob` &ndash; Create a base64 encoded blob from Python source code
* `nr versionupgrade` &ndash; Upgrade version numbers in your project and
  add a Git commit.

### Testing

    nosetests tests

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>
