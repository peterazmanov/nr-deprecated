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

import io
import os
import setuptools
import sys


if any('dist' in x for x in sys.argv[1:]) and os.path.isfile('README.md'):
  try:
    import setuptools_readme
  except ImportError:
    print('Warning: README.rst could not be generated, setuptools_readme module missing.')
  else:
    setuptools_readme.convert('README.md', encoding='utf8')

if os.path.isfile('README.rst'):
  with io.open('README.rst', encoding='utf8') as fp:
    long_description = fp.read()
else:
  print('Warning: README.rst not found, no long_description in setup.')
  long_description = ''


setuptools.setup(
  name='nr',
  version='2.0.7',
  license='MIT',
  description='Compound utility library and command-line tools for Python 2/3',
  long_description=long_description,
  url='https://github.com/NiklasRosenstein/py-nr',
  author='Niklas Rosenstein',
  author_email='rosensteinniklas@gmail.com',
  packages=setuptools.find_packages(),
  install_requires=[],
  entry_points = {
    'console_scripts': [
      'nr = nr.__main__:main'
    ]
  }
)
