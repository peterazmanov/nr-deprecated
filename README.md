## `nr` &ndash; Compound utility library and command-line tools for Python 2/3

This library contains a variety of Python programming utilities that didn't
make it into separate modules. Additionally, this library comes with a bunch
of command-line tools.

Note that most components can be used independently from each other, and some
components may need additional dependencies. These additional dependencies are
currently not automatically installed when install `nr`.

### Components

* `nr.archive` &ndash; Archive handling abstraction
* `nr.concurrency` &ndash; Job scheduling and threaded event processing
* `nr.enum` &ndash; Python 2/3 compatible enumeration class
* `nr.gitignore` &ndash; Parser and evaluator for `.gitignore` files
* `nr.py` &ndash; (Mostly) Generic Python programming tools
* `nr.recordclass` &ndash; Mutable namedtuples with support for default args
* `nr.strex` &ndash; String scanning and lexing facilities
* `nr.version` &ndash; Semantic version parser and evaluator

### Testing

    nosetests tests

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>
