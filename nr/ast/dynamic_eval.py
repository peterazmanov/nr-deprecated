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
This module provides an AST rewriter that takes and Read/Write operations on
global variables and rewrites them to retrieve the variable by a function
instead. Non-global variables are left untouched.

Example:

    import os
    from os import path

    parent_dir = path.dirname(__file__)

    def main():
      filename = path.join(parent_dir, 'foo.py')
      print(filename)

Will be converted to:

    import os; __dict__['os'] = os
    from os import path; __dict__['path'] = path

    __dict__['parent_dir'] = __dict__['path'].dirname(__dict__['__file__'])

    def main():
      filename = __dict__['path'].join(__dict__['parent_dir'], 'foo.py')
      __dict__['print'](filename)
"""

import ast
import collections
import textwrap
from ..compat import builtins, exec_


class NameRewriter(ast.NodeTransformer):

  # This code snippet is inserted when using the `from X import *` syntax.
  IMPORT_FROM_ALL_ASSIGN = textwrap.dedent('''
    # We can not use __import__(module, fromlist=[None]) as some modules seem
    # to break with it (see for example nose-devs/nose#1075).
    import importlib as __importlib
    __module = __importlib.import_module({module!r})
    try:
      __vars = __module.__all__
    except AttributeError:
      __vars = [x for x in dir(__module) if not x.startswith('_')]
    for __key in __vars:
      {data_var}[__key] = getattr(__module, __key)
    del __importlib, __module, __vars, __key
  ''')

  def __init__(self, data_var):
    self.data_var = data_var
    self.stack = []

  def __push_stack(self):
    self.stack.append({'external': set(), 'vars': set()})

  def __pop_stack(self):
    self.stack.pop()

  def __is_local(self, name):
    if not self.stack:
      return False
    return name in self.stack[-1]['vars']

  def __add_variable(self, name):
    if self.stack and name not in self.stack[-1]['external']:
      self.stack[-1]['vars'].add(name)

  def __add_external(self, name):
    if self.stack:
      self.stack[-1]['external'].add(name)

  def __get_subscript(self, name, ctx=None):
    """
    Returns `<data_var>["<name>"]`
    """

    return ast.Subscript(
      value=ast.Name(id=self.data_var, ctx=ast.Load()),
      slice=ast.Index(value=ast.Str(s=name)),
      ctx=ctx)

  def __get_subscript_assign(self, name):
    """
    Returns `<data_var>["<name>"] = <name>`.
    """

    return ast.Assign(
      targets=[self.__get_subscript(name, ast.Store())],
      value=ast.Name(id=name, ctx=ast.Load()))

  def visit_Name(self, node):
    if not self.__is_local(node.id):
      node = ast.copy_location(self.__get_subscript(node.id, node.ctx), node)
    return node

  def visit_Assign(self, node):
    def visit(node):
      if isinstance(node, ast.Name):
        self.__add_variable(node.id)
      elif isinstance(node, ast.Tuple):
        [visit(x) for x in node.elts]
    for target in node.targets:
      visit(target)
    self.generic_visit(node)
    return node

  def visit_Import(self, node):
    assignments = []
    for alias in node.names:
      name = alias.asname or alias.name
      assignments.append(self.__get_subscript_assign(name))
    return [node] + assignments

  def visit_ImportFrom(self, node):
    assignments = []
    for alias in node.names:
      name = alias.asname or alias.name
      if name == '*':
        code = self.IMPORT_FROM_ALL_ASSIGN.format(module=node.module, data_var=self.data_var)
        module = ast.parse(code)
        assignments += module.body
      else:
        assignments.append(self.__get_subscript_assign(name))
    return [node] + assignments

  def visit_FunctionDef(self, node):
    self.__push_stack()
    if isinstance(node, ast.FunctionDef):  # Also used for ClassDef
      for arg in node.args.args + node.args.kwonlyargs:
        self.__add_variable(arg.arg)
      if node.args.vararg:
        self.__add_variable(node.args.vararg.arg)
      if node.args.kwarg:
        self.__add_variable(node.args.kwarg.arg)
    self.generic_visit(node)
    self.__pop_stack()
    assign = self.__get_subscript_assign(node.name)
    return [node, assign]

  visit_ClassDef = visit_FunctionDef

  def visit_Global(self, node):
    for name in node.names:
      self.__add_external(name)

  visit_Nonlocal = visit_Global


def transform(ast_node, data_var='__dict__'):
  ast_node = NameRewriter('__dict__').visit(ast_node)
  ast_node = ast.fix_missing_locations(ast_node)
  return ast_node


def dynamic_exec(code, resolve, assign=None, automatic_builtins=True,
                 filename=None, module_name=None, _type='exec'):
  """
  Transforms the Python source code *code* and evaluates it so that the
  *resolve* and *assign* functions are called respectively for when a global
  variable is access or assigned.

  If *resolve* is a mapping, *assign* must be omitted. #KeyError#s raised by
  the mapping are automatically converted to #NameError#s.

  Otherwise, *resolve* and *assign* must be callables that have the same
  interface as `__getitem__()`, and `__setitem__()`. If *assign* is omitted
  in that case, assignments will be redirected to a separate dictionary and
  keys in that dictionary will be checked before continuing with the *resolve*
  callback.
  """

  parse_filename = filename or '<string>'
  ast_node = transform(ast.parse(code, parse_filename, mode=_type))
  code = compile(ast_node, parse_filename, _type)
  if hasattr(resolve, '__getitem__'):
    if assign is not None:
      raise TypeError('"assign" parameter specified where "resolve" is a mapping')
    input_mapping = resolve

    def resolve(x):
      try:
        return input_mapping[x]
      except KeyError:
        raise NameError(x)

    assign = input_mapping.__setitem__
  else:
    input_mapping = False

  class DynamicMapping(object):
    _data = {}
    def __repr__(self):
      if input_mapping:
        return 'DynamicMapping({!r})'.format(input_mapping)
      else:
        return 'DynamicMapping(resolve={!r}, assign={!r})'.format(resolve, assign)
    def __getitem__(self, key):
      if assign is None:
        try:
          return self._data[key]
        except KeyError:
          pass  # Continue with resolve()
      try:
        return resolve(key)
      except NameError:
        if automatic_builtins:
          try:
            return getattr(builtins, key)
          except AttributeError:
            pass
        raise
    def __setitem__(self, key, value):
      if assign is None:
        self._data[key] = value
      else:
        assign(key, value)
    def get(self, key, default=None):
      try:
        return self[key]
      except NameError:
        return default

  mapping = DynamicMapping()
  globals_ = {'__dict__': mapping}

  if filename:
    mapping['__file__'] = filename
    globals_['__file__'] = filename

  if module_name:
    mapping['__name__'] = module_name
    globals_['__name__'] = module_name

  return (exec_ if _type == 'exec' else eval)(code, globals_)


def dynamic_eval(*args, **kwargs):
  return dynamic_exec(*args, _type='eval', **kwargs)
