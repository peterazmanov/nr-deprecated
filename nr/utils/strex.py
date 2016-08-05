# Copyright (C) 2015-2016  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
'''
`nr.utils.strex` String Processing Library
==========================================

Strex is a simple library to tokenize and parse small or even
complex languages. It has been developed specifically for the
recursive decent parser technique, although it might work well
with other parsing techniques as well.
'''

import collections
import string
import re
import sys

__author__ = 'Niklas Rosenstein <rosensteinniklas(at)gmail.com>'
__version__ = '1.4.1'

eof = 'eof'
string_types = (str,) if sys.version_info[0] == 3 else (str, unicode)

Cursor = collections.namedtuple('Cursor', 'index lineno colno')
Token = collections.namedtuple('Token', 'type cursor value')


class Scanner(object):
  ''' This class is used to step through text character by character
  and keep track of the line and column numbers of each passed
  character. The Scanner will only tread line-feed as a newline.

  @param text
    The text to parse. Must be a `str` in Python 3 and may also be
    a `unicode` object in Python 2.

  @attr text
  @attr index The index in the text.
  @attr lineno The current line number.
  @attr colno The current column number.
  @property cursor The current `Cursor` value.
  @property char The current character, or an empty string/unicode
    if the end of the text was reached. '''

  def __init__(self, text):
    if not isinstance(text, string_types):
      raise TypeError('expected str or unicode', type(text))
    super(Scanner, self).__init__()
    self.text = text
    self.index = 0
    self.lineno = 1
    self.colno = 0

  def __repr__(self):
    return '<Scanner at {0}:{0}>'.format(self.lineno, self.colno)

  def __bool__(self):
    return self.index < len(self.text)

  __nonzero__ = __bool__  # Python 2

  @property
  def cursor(self):
    return Cursor(self.index, self.lineno, self.colno)

  @property
  def char(self):
    if self.index >= 0 and self.index < len(self.text):
      return self.text[self.index]
    else:
      return type(self.text)()

  def next(self):
    ''' Move on to the next character in the scanned text. '''

    char = self.char
    if char == '\n':
      self.lineno += 1
      self.colno = 0
    else:
      self.colno += 1
    self.index += 1

  def next_get(self):
    ''' Like `next()` but returns the new character. '''

    self.next()
    return self.char

  def restore(self, cursor):
    ''' Moves the scanner back (or forward) to the specified cursor. '''

    if not isinstance(cursor, Cursor):
      raise TypeError('expected Cursor object', type(cursor))
    self.index, self.lineno, self.colno = cursor


def readline(scanner):
  ''' Reads a full line from the *scanner* and returns it. This is
  fast over using `Scanner.next()` to the line-feed. The resulting
  string contains the line-feed character if present. '''

  start = end = scanner.index
  while end < len(scanner.text):
    if scanner.text[end] == '\n':
      end += 1
      break
    end += 1
  result = scanner.text[start:end]
  scanner.index = end
  if result.endswith('\n'):
    scanner.colno = 0
    scanner.lineno += 1
  else:
    scanner.colno += end - start
  return result


def match(scanner, regex, flags=0):
  ''' Matches the specified *regex* from the current character of the
  *scanner* and returns a match object or None if it didn't match. The
  Scanners column and line numbers are updated respectively. '''

  if isinstance(regex, str):
    regex = re.compile(regex, flags)
  match = regex.match(scanner.text, scanner.index)
  if not match:
    return None
  start, end = match.start(), match.end()
  lines = scanner.text.count('\n', start, end)
  scanner.index = end
  if lines:
    scanner.colno = end - scanner.text.rfind('\n', start, end) - 1
    scanner.lineno += lines
  else:
    scanner.colno += end - start
  return match


class Lexer(object):
  ''' This class is used to split text into `Token`s using a
  `Scanner` and a list of `Rule`s. If *raise_invalid* is True, it
  raises an `TokenizationError` instead of yielding an invalid
  `Token` object.

  @param scanner The `Scanner` to use for lexing.
  @param rules A list of `Rule` objects.
  @param raise_invalid True if an exception should be raised when
    the stream can not be tokenized, False if it should just yield
    an invalid token and proceed with the next character.

  @attr scanner
  @attr rules
  @attr rules_map A dictionary mapping the rule name to the rule
    object. This is automatically built when the Lexer is created.
    If the `rules` are updated in the lexer directly, `update()`
    must be called.
  @attr skippable_rules A list of skippable rules built from the
    `rules` list. `update()` must be called if any of the rules
    or rules list are modified.
  @attr raise_invalid
  @attr skip_rules A set of rule type IDs that will automatically
    be skipped by the `next()` method.
  @attr token The current `Token`. After the Lexer is created and
    the `next()` method has not been called, the value of this
    attribute is None. At the end of the input, the token is of
    type `eof`.
  '''

  def __init__(self, scanner, rules=None, raise_invalid=True):
    super(Lexer, self).__init__()
    self.scanner = scanner
    self.rules = list(rules) if rules else []
    self.update()
    self.raise_invalid = raise_invalid
    self.token = None

  def __repr__(self):
    ctok = self.token.type if self.token else None
    return '<Lexer with current token {0!r}>'.format(ctok)

  def __iter__(self):
    if not self.token:
      self.next()
    while not self.token.type == eof:
      yield self.token
      self.next()

  def __bool__(self):
    if self.token and self.token.type == eof:
      return False
    return True

  __nonzero__ = __bool__  # Python 2

  def update(self):
    ''' Updates the `rules_map` dictionary and `skippable_rules` list
    based on the `rules` list.

    Raises:
      ValueError: if a rule name is duplicate
      TypeError: if an item in the `rules` list is not a rule. '''

    self.rules_map = {}
    self.skippable_rules = []
    for rule in self.rules:
      if not isinstance(rule, Rule):
        raise TypeError('item must be Rule instance', type(rule))
      if rule.name in self.rules_map:
        raise ValueError('duplicate rule name', rule.name)
      self.rules_map[rule.name] = rule
      if rule.skip:
        self.skippable_rules.append(rule)

  def expect(self, *names):
    ''' Checks if the _current_ token matches one of the specified
    token type names and raises `UnexpectedTokenError` if it does not. '''

    if not names:
      return
    if not self.token or self.token.type not in names:
      raise UnexpectedTokenError(names, self.token)

  def accept(self, *names, **kwargs):
    ''' Extracts a token of one of the specified rule names and doesn't
    error if unsuccessful. Skippable tokens might still be skipped by
    this method.

    Raises:
      ValueError: if a rule with the specified name doesn't exist. '''

    return self.next(*names, as_accept=True, **kwargs)

  def next(self, *expectation, **kwargs):
    ''' Parse the next token from the input and return it. If
    `raise_invalid` is True, this method can raise `TokenizationError`.
    The new token can also be accessed from the `token` attribute
    after the method was called.

    If one or more arguments are specified, they must be rule names
    that are to be expected at the current position. They will be
    attempted to be matched first (in the specicied order). If the
    expectation could not be met, a `UnexpectedTokenError` is raised.

    An expected Token will not be skipped, even if its rule says so.

    Arguments:
      \*expectation: The name of one or more rules that are expected
        from the current context of the parser. If empty, the first
        matching token of all rules will be returned. Skippable tokens
        will always be skipped unless specified as argument.
      as_accept=False: If passed True, this method behaves
        the same as the `accept()` method.
      weighted=False: If passed True, the *\*expectation* tokens
        are checked before the default token order.

    Raises:
      ValueError: if an expectation doesn't match with a rule name.
      UnexpectedTokenError: if an expectation is given and the
        expectation wasn't fulfilled.
      TokenizationError: if a token could not be generated from
        the current position of the Scanner and `raise_invalid`
        is True.
    '''

    as_accept = kwargs.pop('as_accept', False)
    weighted = kwargs.pop('weighted', False)
    for key in kwargs:
      raise TypeError('unexpected keyword argument {0!r}'.format(key))

    if self.token and self.token.type == eof:
      if not as_accept and expectation and eof not in expectation:
        raise UnexpectedTokenError(expectation, self.token)
      elif as_accept and eof in expectation:
        return self.token
      elif as_accept:
        return None
      return self.token

    token = None
    while token is None:
      # Stop if we reached the end of the input.
      cursor = self.scanner.cursor
      if not self.scanner:
        token = Token(eof, cursor, None)
        break

      value = None

      # Try to match the expected tokens.
      if weighted:
        for rule_name in expectation:
          if rule_name == eof:
            continue
          rule = self.rules_map.get(rule_name)
          if rule is None:
            raise ValueError('unknown rule', rule_name)
          value = rule.tokenize(self.scanner)
          if value:
            break
          self.scanner.restore(cursor)

      # Match the rest of the rules, but only if we're not acting
      # like the accept() method that doesn't need the next token
      # for raising an UnexpectedTokenError.
      if not value:
        if as_accept and weighted:
          # Check only skippable rules if we're only trying to accept
          # a certain token type and may consume any skippable tokens
          # until then.
          check_rules = self.skippable_rules
        else:
          check_rules = self.rules
        for rule in check_rules:
          if weighted and expectation and rule.name in expectation:
            # Skip rules that we already tried.
            continue
          value = rule.tokenize(self.scanner)
          if value:
            break
          self.scanner.restore(cursor)

      if not value:
        if as_accept:
          return None
        token = Token(None, cursor, self.scanner.char)
      else:
        assert rule, "we should have a rule by now"
        if type(value) is not Token:
          value = Token(rule.name, cursor, value)
        token = value

        expected = rule.name in expectation
        if not expected and rule.skip:
          # If we didn't expect this rule to match, and if its skippable,
          # just skip it. :-)
          token = None
        elif not expected and as_accept:
          # If we didn't expect this rule to match but are just accepting
          # instead of expecting, restore to the original location and stop.
          self.scanner.restore(cursor)
          return None

    self.token = token
    if as_accept and token and token.type == eof:
      if eof in expectation:
        return token
      return None

    if token.type is None:
      raise TokenizationError(token)
    if not as_accept and expectation and token.type not in expectation:
      raise UnexpectedTokenError(expectation, token)
    assert not as_accept or (token and token.type in expectation)
    return token


class Rule(object):
  ''' Base class for rule objects that are capable of extracting a
  `Token` from the current position of a `Scanner`. '''

  def __init__(self, name, skip=False):
    super(Rule, self).__init__()
    self.name = name
    self.skip = skip

  def tokenize(self, scanner):
    ''' Attempt to extract a token from the position of the *scanner*
    and return it. If a non-`Token` instance is returned, it will be
    used as the tokens value. Any value that evaluates to False will
    make the Lexer assume that the rule couldn't capture a Token.

    The `Token.value` must not necessarily be a string though, it can
    be any data type or even a complex datatype, only the user must
    know about it and handle the tokens special. '''

    raise NotImplementedError


class Regex(Rule):
  ''' A rule to match a regular expression. The `Token` generated by
  this rule contains the match object as its value. '''

  def __init__(self, name, regex, flags=0, skip=False):
    super(Regex, self).__init__(name, skip)
    if isinstance(regex, string_types):
      regex = re.compile(regex, flags)
    self.regex = regex

  def tokenize(self, scanner):
    result = match(scanner, self.regex)
    if result is None or result.start() == result.end():
      return None
    return result


class Keyword(Rule):
  ''' This rule matches an exact string (optionally case insensitive)
  from the scanners current position. '''

  def __init__(self, name, string, case_sensitive=True, skip=False):
    super(Keyword, self).__init__(name, skip)
    self.string = string
    self.case_sensitive = case_sensitive

  def tokenize(self, scanner):
    string = self.string if self.case_sensitive else self.string.lower()
    char = scanner.char
    result = type(char)()
    for other_char in string:
      if not self.case_sensitive:
        char = char.lower()
      if char != other_char:
        return None
      result += char
      char = scanner.next_get()
    return result


class Charset(Rule):
  ''' This rule consumes all characters of a given set. It can be
  specified to only match at a specific column number of the scanner.
  This is useful to create a separate indentation token type apart
  from the typical whitespace token. '''

  def __init__(self, name, charset, at_column=-1, skip=False):
    super(Charset, self).__init__(name, skip)
    self.charset = frozenset(charset)
    self.at_column = at_column

  def tokenize(self, scanner):
    if self.at_column >= 0 and self.at_column != scanner.colno:
      return None
    char = scanner.char
    result = type(char)()
    while char and char in self.charset:
      result += char
      char = scanner.next_get()
    return result


class TokenizationError(Exception):
  ''' This exception is raised if the stream can not be tokenized
  at a given position. The `Token` object that an object is initialized
  with is an invalid token with the cursor position and current scanner
  character as its value. '''

  def __init__(self, token):
    if type(token) is not Token:
      raise TypeError('expected Token object', type(token))
    if token.type is not None:
      raise ValueError('can not be raised with a valid token')
    self.token = token

  def __str__(self):
    message = 'could not tokenize stream at {0}:{1}:{2!r}'.format(
      self.token.cursor.lineno, self.token.cursor.colno, self.token.value)
    return message


class UnexpectedTokenError(Exception):
  ''' This exception is raised when the `Lexer.next()` method was given
  one or more expected token types but the extracted token didn't match
  the expected types. '''

  def __init__(self, expectation, token):
    if not isinstance(expectation, (list, tuple)):
      message = 'expectation must be a list/tuple of rule names'
      raise TypeError(message, type(expectation))
    if len(expectation) < 1:
      raise ValueError('expectation must contain at least one item')
    if type(token) is not Token:
      raise TypeError('token must be Token object', type(token))
    if token.type is None:
      raise ValueError('can not be raised with an invalid token')
    self.expectation = expectation
    self.token = token

  def __str__(self):
    message = 'expected token '.format(self.token.cursor.lineno, self.token.cursor.colno)
    if len(self.expectation) == 1:
      message += '"' + self.expectation[0] + '"'
    else:
      message += '{' + ','.join(map(str, self.expectation)) + '}'
    return message + ', got "{0}" instead (value={1!r} at {2}:{3})'.format(
      self.token.type, self.token.value, self.token.cursor.lineno,
      self.token.cursor.colno)
