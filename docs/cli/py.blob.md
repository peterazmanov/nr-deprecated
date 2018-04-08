```
usage: nr py.blob [-h] [-o OUTPUT] [-c] [-m] [-O] [-w LINE_WIDTH]
                  [-s {direct,default}] [-e EXPORT_SYMBOL]
                  sourcefile

Create a base64 encoded, optionally compressed and minified blob of a Python
source file. Note that the -O,--minify-obfuscate option does not always work
(eg. when using a variable 'file' in a Python 3.6 source file) due to
incompatibilities in pyminifier.

positional arguments:
  sourcefile

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
  -c, --compress
  -m, --minify
  -O, --minify-obfuscate
  -w LINE_WIDTH, --line-width LINE_WIDTH
  -s {direct,default}, --store-method {direct,default}
  -e EXPORT_SYMBOL, --export-symbol EXPORT_SYMBOL
```
