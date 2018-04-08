```
usage: nr grablicense [-h] [-l] [-s] [--python] [--java] [--cpp] [--c]
                      [--badge]
                      [license] [author]

Output a license string, optionally formatted for the specified language.
Prints a list of the supported licenses when no arguments are passed. When the
AUTHOR is specified, the <year> and <author> will be replaced in the output
license string.

positional arguments:
  license
  author

optional arguments:
  -h, --help   show this help message and exit
  -l, --list   List available licenses.
  -s, --short  Get the license's short version.
  --python     Format for Python code.
  --java       Format for Java code.
  --cpp        Format for C++ code.
  --c          Format for C code.
  --badge      Output Markdown code for a badge for the specified license.
```
