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
"""
This module minifies and compressed Python source code to a base64 encoded
blob. The minification feature requires the `pyminifier` command-line tool
to be installed.
"""

import argparse
import base64
import os
import subprocess
import sys
import tempfile
import textwrap
import zlib

DECODE_NONE = 'blob'
DECODE_B64 = 'b.b64decode(blob)'
DECODE_B64ZLIB = 'z.decompress(b.b64decode(blob))'

EXEC_TEMPLATE = '''
import base64 as b, types as t, zlib as z; m=t.ModuleType({name!r});
m.__file__ = __file__; blob={blobdata}
exec({decode}, vars(m)); {storemethod}
del blob, b, t, z, m;
'''

STOREMETHOD_SYMBOL = '_{name}=m;{symbol}=getattr(m,"{symbol}")'
STOREMETHOD_DIRECT = '{name}=m'


def silent_remove(filename):
  try:
    os.remove(filename)
  except OSError as exc:
    if exc.errno != errno.ENONENT:
      raise


def minify(code, obfuscate=False):
  fp = None
  try:
    with tempfile.NamedTemporaryFile(delete=False) as fp:
      fp.write(code.encode('utf8'))
      fp.close()
      args = ['pyminifier', fp.name]
      if obfuscate:
        args.insert(1, '-O')
      popen = subprocess.Popen(args,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
      result = popen.communicate()[0].decode('utf8')
    if popen.returncode != 0:
      raise OSError('pyminifier exited with returncode {0!r}'.format(popen.returncode))
  finally:
    if fp is not None:
      silent_remove(fp.name)
  return result.replace('\r\n', '\n')


def mkblob(name, code, compress=False, minify=False, minify_obfuscate=False,
           line_width=79, export_symbol=None, blob=True):
  if minify:
    code = globals()['minify'](code, minify_obfuscate)

  # Compress the code, if desired, and convert to Base64.
  if not compress and not blob:
    code = code.replace('\\', '\\\\').replace('"""', '\\"\\"\\"')
  data = code.encode('utf8')
  if compress:
    data = zlib.compress(data)
    decode = DECODE_B64ZLIB
  elif blob:
    decode = DECODE_B64
  else:
    decode = DECODE_NONE
  if compress or blob:
    data = base64.b64encode(data).decode('ascii')
    lines = "b'\\\n" + '\\\n'.join(textwrap.wrap(data, width=line_width)) + "'"
  else:
    lines = '"""' + data.decode('utf8') + '"""'

  if export_symbol:
    storemethod = STOREMETHOD_SYMBOL.format(name=name, symbol=export_symbol)
  else:
    storemethod = STOREMETHOD_DIRECT.format(name=name)

  return EXEC_TEMPLATE.format(name=name, blobdata=lines, storemethod=storemethod, decode=decode)


def main(prog=None, argv=None):
  parser = argparse.ArgumentParser(prog=prog, description="""
    Create a base64 encoded, optionally compressed and minified blob of a
    Python source file. Note that the -O,--minify-obfuscate option does not
    always work (eg. when using a variable 'file' in a Python 3.6 source
    file) due to incompatibilities in pyminifier.
  """)
  parser.add_argument('sourcefile', type=argparse.FileType('r'))
  parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout)
  parser.add_argument('-c', '--compress', action='store_true')
  parser.add_argument('-m', '--minify', action='store_true')
  parser.add_argument('-O', '--minify-obfuscate', action='store_true')
  parser.add_argument('-w', '--line-width', type=int, default=79)
  parser.add_argument('-s', '--store-method', choices=('direct', 'default'))
  parser.add_argument('-e', '--export-symbol')
  args = parser.parse_args(argv)

  name = os.path.splitext(os.path.basename(args.sourcefile.name))[0]
  args.output.write(mkblob(name=name, code=args.sourcefile.read(),
      minify=args.minify, compress=args.compress,
      minify_obfuscate=args.minify_obfuscate, line_width=args.line_width,
      export_symbol=args.export_symbol))


if __name__ == "__main__":
  sys.exit(main())
