+++
description = "Generat executable base64 encoded blobs from Python code."
+++

## Requirements

* [pyminifier](https://github.com/liftoff/pyminifier) command-line (optional,
  required for minification before encoding)

## `mkblob()`

__Parameters__

* name
* code
* compress=False
* minify=False
* minify_obfuscate=False
* line_width=79
* export_symbol=None
* blob=True
