# The MIT License (MIT)
#
# Copyright (c) 2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import print_function
import argparse
import datetime
import os
import sys

LICENSES_DIR = os.path.join(os.path.dirname(__file__), 'licenses')


def main(prog=None, argv=None):
  parser = argparse.ArgumentParser(prog=prog, description="""
    Output a license string, optionally formatted for the specified
    language. Prints a list of the supported licenses when no arguments are
    passed. When the AUTHOR is specified, the <year> and <author> will be
    replaced in the output license string.
  """)
  parser.add_argument('license', nargs='?')
  parser.add_argument('author', nargs='?')
  parser.add_argument('-l', '--list', action='store_true', help='List available licenses.')
  parser.add_argument('-s', '--short', action='store_true', help='Get the license\'s short version.')
  parser.add_argument('--python', action='store_true', help='Format for Python code.')
  parser.add_argument('--java', action='store_true', help='Format for Java code.')
  parser.add_argument('--cpp', action='store_true', help='Format for C++ code.')
  parser.add_argument('--c', action='store_true', help='Format for C code.')
  args = parser.parse_args(argv)

  if not args.license and not args.list:
    parser.print_usage()
    return 1

  if args.list:
    for name in (x.name for x in LICENSES_DIR.iterdir()):
      print(name)
    return

  directory = LICENSES_DIR.joinpath(args.license)
  if not directory.is_dir():
    print('fatal: unsupported license: "{}"'.format(args.license), file=sys.stderr)
    return 1

  filename = 'LICENSE_SHORT.txt' if args.short else 'LICENSE.txt'
  filename = directory.joinpath(filename)
  if args.short and not filename.is_file():
    filename = directory.joinpath('LICENSE.txt')

  if args.python:
    prefix = (None, '# ', '# ', None)
  elif args.c or args.cpp:
    prefix = (None, '/* ', ' * ', ' */')
  elif args.java:
    prefix = ('/**', ' * ', ' * ', '*/')
  else:
    prefix = (None, None, None, None)

  year = str(datetime.date.today().year)

  with filename.open() as fp:
    if prefix[0]:
      print(prefix[0])
    for index, line in enumerate(fp):
      if args.author:
        line = line.replace('<year>', year)
        line = line.replace('<author>', args.author)
      if index == 0 and prefix[1]:
        print(prefix[1], end='')
      elif index > 0 and prefix[2]:
        print(prefix[2], end='')
      print(line, end='')
    if not line.endswith('\n'):
      print()
    if prefix[3]:
      print(prefix[3])


if __name__ == '__main__':
  sys.exit(main())
