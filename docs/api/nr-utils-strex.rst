:mod:`nr.utils.strex` --- String procesing & parsing
====================================================

.. module:: nr.utils.strex
  :synopsis: String procesing & parsing

:mod:`~nr.utils.strex` is a simple library to tokenize and parse small
or even complex languages. It has been developed specifically for the
recursive decent parser technique, although it might work well with other
parsing techniques as well.

Features
--------

- ``Scanner`` class for very simple tasks
- ``Lexer`` class for tokenizing text input
- Control tokenization via ``Rule`` s
- Contextual tokenization

Example
-------

To describe a set of rules to tokenize a text, you simply have to
create a list. You can re-use that list with multiple lexers.

.. code:: python

  rules = [
    nr.strex.Keyword('bopen', '{'),
    nr.strex.Keyword('bclose', '}'),
    nr.strex.Keyword('semicolon', ';'),
    nr.strex.Keyword('group', 'GROUP'),
    nr.strex.Keyword('menu', 'MENU'),
    nr.strex.Charset('ident', string.ascii_letters + string.digits + '_'),
    nr.strex.Charset('ws', string.whitespace, skip=True),
  ]

Now you can use the lexer to tokenize the stream. Iterating over the
lexer is like getting the next token until the end of the input (that
will yield a token with type ``'eof'``). In a context sensitive parser
architecture, you can pass arguments to ``Lexer.next()`` or use the
``Lexer.accept()`` method to prioritize or expect a specific token type.

.. code:: python

  text = '''
    GROUP {
      MENU FOOBAR;
      MENU SPAM;
      GROUP { MENU HAM; }
    } '''
  scanner = nr.strex.Scanner(text)
  lexer = nr.strex.Lexer(scanner, rules)
  for token in lexer:
    print(token)

Outputs:

::

  Token(type='group', cursor=Cursor(index=1, lineno=2, colno=0), value='GROUP')
  Token(type='bopen', cursor=Cursor(index=7, lineno=2, colno=6), value='{')
  Token(type='menu', cursor=Cursor(index=11, lineno=3, colno=2), value='MENU')
  Token(type='ident', cursor=Cursor(index=16, lineno=3, colno=7), value='FOOBAR')
  Token(type='semicolon', cursor=Cursor(index=22, lineno=3, colno=13), value=';')
  Token(type='menu', cursor=Cursor(index=26, lineno=4, colno=2), value='MENU')
  Token(type='ident', cursor=Cursor(index=31, lineno=4, colno=7), value='SPAM')
  Token(type='semicolon', cursor=Cursor(index=35, lineno=4, colno=11), value=';')
  Token(type='group', cursor=Cursor(index=39, lineno=5, colno=2), value='GROUP')
  Token(type='bopen', cursor=Cursor(index=45, lineno=5, colno=8), value='{')
  Token(type='menu', cursor=Cursor(index=47, lineno=5, colno=10), value='MENU')
  Token(type='ident', cursor=Cursor(index=52, lineno=5, colno=15), value='HAM')
  Token(type='semicolon', cursor=Cursor(index=55, lineno=5, colno=18), value=';')
  Token(type='bclose', cursor=Cursor(index=57, lineno=5, colno=20), value='}')
  Token(type='bclose', cursor=Cursor(index=59, lineno=6, colno=0), value='}')
