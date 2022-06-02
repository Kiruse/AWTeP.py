from __future__ import annotations
from typing import *
from .ast import *
from .error import ParserError, RedirectError, SkipNode
from .interface.logger import Logger
from .source_reader import SourceReader

def parse(source: str, *, logger: Logger | None = None) -> ASTList:
  """Parse raw WikiText source code as unbiased text"""
  terminator = lambda r: len(r) == 0
  return parse_text(SourceReader(source, logger=logger), terminators=terminator, no_eof=False, strip='both')

def parsepage(source: str, file: str = '', *, logger: Logger | None = None) -> Tuple[ASTList, ASTList]:
  """Parse the WikiText of a template. Returns [directives, AST] tuple."""
  terminator = lambda r: len(r) == 0
  
  logger and file and logger.d(f'Parsing template {file}')
  reader = SourceReader(source, file, logger)
  directives = parse_directives(reader)
  ast = parse_text(reader, terminators=terminator, no_eof=False, strip='both')
  logger and file and logger.d(f'Finished parsing template {file}')
  return directives, ast


def parse_directives(reader: SourceReader) -> ASTList:
  directives = []
  while True:
    readercopy = reader.copy()
    consume_blanklines(readercopy)
    try:
      directives.append(parse_directive(readercopy))
      reader.skip(len(reader) - len(readercopy))
    except ParserError:
      break
  return directives

def parse_directive(reader: SourceReader) -> AST:
  if reader.peeks('__toc__', case_sensitive=False, no_eof=False):
    return AST('toc')
  if reader.peeks('__notoc__', case_sensitive=False, no_eof=False):
    return AST('notoc')
  
  if reader.next() != '#':
    raise ParserError('Expected # (start of directive)', reader)
  
  consume_whitespace(reader)
  
  if reader.consume('redirect', case_sensitive=False) or reader.consume('weiterleitung', case_sensitive=False):
    consume_whitespace(reader)
    link = parse_link(reader)
    raise RedirectError(link.children[1], reader.file)
  else:
    raise ParserError('Unknown directive', reader)

def parse_heading(reader: SourceReader) -> HeadingNode:
  if not reader.peeks('='):
    raise ParserError('Expected heading', reader)
  
  level = consume_count(reader, '=')
  if level > 6:
    raise ParserError('Heading level too high', reader)
  
  title = parse_text(reader, terminators='=\n', strip='both')
  
  if not reader.consume('=' * level):
    raise ParserError(f'Unexpected {reader.peek()}, expected {"=" * level} (end of heading)', reader)
  consume_trailing_space(reader)
  
  return HeadingNode(title, level)

def parse_template(reader: SourceReader) -> TemplateNode:
  if not reader.consume('{{'):
    raise ParserError('Expected "{{" (start of template)', reader)
  
  name = parse_template_name(reader)
  posargs, namedargs = parse_template_args(reader)
  
  if not reader.consume('}}'):
    raise ParserError('Expected "}}" (end of template)', reader)
  return TemplateNode(name, posargs, namedargs)

def parse_template_name(reader: SourceReader) -> ASTList:
  result: ASTList = []
  txt = ''
  
  isterminated = lambda: reader.peek() in '|}'
  
  while not isterminated():
    if reader.peeks('{'):
      txt and result.append(TextNode(txt))
      txt = ''
      
      try:
        result.append(parse_braces(reader))
      except ParserError:
        raise ParserError('Illegal reserved character "{"', reader)
    else:
      txt += reader.next()
  
  txt and result.append(TextNode(txt))
  return trim_text_nodes(result)

def parse_template_args(reader: SourceReader) -> Tuple[List[PosArgNode], List[NamedArgNode]]:
  """Parse template arguments split into two lists of positional
  arguments and named arguments."""
  posargs = []
  namedargs = []
  
  def parse_arg():
    copy = reader.copy()
    if consume_pipe(copy, optional=True):
      return parse_template_arg(reader)
    else:
      return None
  
  while arg := parse_arg():
    if arg.name == 'posarg':
      posargs.append(arg)
    elif arg.name == 'namedarg':
      namedargs.append(arg)
    else:
      raise ValueError(f'Unknown argument type {arg.name}')
  return posargs, namedargs

def parse_template_arg(reader: SourceReader) -> PosArgNode | NamedArgNode:
  consume_pipe(reader)
  
  try:
    with reader.consumer() as consumer:
      name = parse_variable_name(consumer, delims='=|}')
      if not consumer.consume('='):
        raise ParserError('expected equals (key-value pair)', consumer)
      value = parse_text(consumer, terminators='|}', strip='both')
      return NamedArgNode(name, value)
  except ParserError:
    value = parse_text(reader, terminators='|}', strip='both')
    return PosArgNode(value)

def parse_variable(reader: SourceReader) -> VariableNode:
  if not reader.consume('{{{'):
    raise ParserError(f'Unexpected character {reader.peek()}, expected {"{{{"} (start of variable)', reader)
  
  name = parse_variable_name(reader)
  
  defaults = None
  if reader.consume('|'):
    defaults = parse_text(reader, terminators='}')
  
  if not reader.consume('}}}'):
    raise ParserError(f'Unexpected character {reader.peek()}, expected {"}}}"} (end of variable)', reader)
  
  return VariableNode(name, defaults)

def parse_variable_name(reader: SourceReader, delims: Sequence[str] = '|}') -> ASTList:
  result: ASTList = []
  
  isterminated = lambda: reader.peek() in delims
  txt = ''
  
  while not isterminated():
    if reader.peeks('{'):
      txt and result.append(TextNode(txt))
      txt = ''
      
      if reader.peeks('{{{'):
        result.append(parse_variable(reader))
      else:
        raise ParserError('Illegal reserved character "{"', reader)
    else:
      txt += reader.next()
  
  txt and result.append(TextNode(txt))
  return trim_text_nodes(result)

def is_function(reader: SourceReader) -> bool:
  copy = reader.copy()
  if not copy.consume('{{'):
    return False
  consume_any_whitespace(copy)
  return copy.consume('#')

def parse_function(reader: SourceReader) -> ConditionalNode:
  # See https://en.wikipedia.org/wiki/Help:Magic_words#Parser_functions for all parser functions
  if not is_function(reader):
    raise ParserError('Expected start of function (e.g. "{{#")', reader)
  
  reader.consume('{{')
  consume_any_whitespace(reader)
  reader.consume('#')
  consume_any_whitespace(reader)
  
  if reader.peeks('if:'):
    return _parse_function_if(reader)
    
  elif reader.peeks('ifeq:'):
    return _parse_function_ifeq(reader)
  
  elif reader.peeks('ifexist:'):
    return _parse_function_ifexist(reader)
  
  elif reader.peeks('switch:'):
    return _parse_function_switch(reader)
  
  elif reader.peeks('invoke:'):
    return _parse_function_invoke(reader)
  
  else:
    raise ParserError('Unknown flow control', reader)

def _parse_function_if(reader: SourceReader) -> IfNode:
  if not reader.consume('if:'):
    raise ParserError('Expected "if:" (start of if clause)', reader)
  
  condition = parse_text(reader, terminators=tplterm, strip='both')
  consume_pipe(reader)
  
  true = parse_text(reader, terminators=tplterm, strip='both')
  
  false = []
  if consume_pipe(reader, optional=True):
    false = parse_text(reader, terminators=tplterm, strip='both')
  consume_pipe(reader, optional=True)
  consume_tpl_close(reader)
  
  return IfNode(condition, true, false)

def _parse_function_ifeq(reader: SourceReader) -> IfEqNode:
  if not reader.consume('ifeq:'):
    raise ParserError('Expected "ifeq:" (start of comparison clause)', reader)
  
  lhs = parse_text(reader, terminators=tplterm, strip='both')
  consume_pipe(reader)
  
  rhs = parse_text(reader, terminators=tplterm, strip='both')
  consume_pipe(reader)
  
  true = parse_text(reader, terminators=tplterm, strip='both')
  
  false = []
  if consume_pipe(reader, optional=True):
    false = parse_text(reader, terminators=tplterm, strip='both')
  consume_pipe(reader, optional=True)
  consume_tpl_close(reader)
  
  return IfEqNode(lhs, rhs, true, false)

def _parse_function_ifexist(reader: SourceReader) -> IfExistNode:
  if not reader.consume('ifexist:'):
    raise ParserError('Expected "ifexist:" (start of existential clause)', reader)
  
  file = parse_template_name(reader)
  consume_pipe(reader)
  
  true = parse_text(reader, terminators=tplterm, strip='both')
  
  false = []
  if consume_pipe(reader, optional=True):
    false = parse_text(reader, terminators=tplterm, strip='both')
  consume_pipe(reader, optional=True)
  consume_tpl_close(reader)
  
  return IfExistNode(file, true, false)

def _parse_function_switch(reader: SourceReader) -> SwitchNode:
  if not reader.consume('switch:'):
    raise ParserError('Expected "switch:" statement', reader)
  
  val = parse_text(reader, terminators=tplterm, strip='both')
  consume_pipe(reader)
  
  branches = []
  while True:
    branches.extend(_parse_function_switch_branch(reader))
    if not consume_pipe(reader, optional=True):
      break
  consume_tpl_close(reader)
  return SwitchNode(val, branches)

def _parse_function_switch_branch(reader: SourceReader) -> SwitchBranchNode:
  refs = []
  
  def addref():
    with reader.consumer() as consumer:
      ast = parse_text(consumer, terminators='=|}', strip='both')
      copy = consumer.copy()
      if consume_tpl_close(copy, optional=True):
        refs.append([TextNode('#default')])
        consumer.revert()
      else:
        refs.append(ast)
  
  addref()
  while consume_pipe(reader, optional=True):
    addref()
  
  # two cases:
  # 1) named branch with = designating substitution
  # 2) unnamed default branch at the end of the switch statement
  if reader.consume('='):
    rep = parse_text(reader, terminators=tplterm, strip='both')
  else:
    rep = parse_text(reader, terminators=tplterm, strip='both')
    if not consume_tpl_close(reader.copy()): # do not actually consume - it is consumed by parent function
      raise ParserError('Expected switch branch value', reader)
  return map(lambda ref: SwitchBranchNode(ref, rep), refs)

def _parse_function_invoke(reader: SourceReader) -> InvokeNode:
  # NOTE: technically called a "magic word".
  # I have no clue what the difference is between magic words & parser functions.
  if not reader.consume('invoke:'):
    raise ParserError('Expected "invoke:" (start of invocation)', reader)
  
  module = parse_template_name(reader)
  consume_pipe(reader)
  function = parse_template_name(reader)
  posargs, namedargs = parse_template_args(reader)
  consume_tpl_close(reader)
  
  return InvokeNode(module, function, posargs, namedargs)

def parse_text(
  reader: SourceReader,
  *,
  terminators: Union[str, Callable[[SourceReader], bool]] = '\n',
  no_eof: bool = True,
  strip: Literal['none', 'left', 'right', 'both'] = 'none',
) -> ASTList:
  """Returns text AST, which includes plain text and various formattings,
  together with the corresponding terminator characters (from `terminators`)."""
  value = ''
  values: List[AST] = []
  
  def isterminated():
    try:
      copy = reader.copy()
      return terminators(copy)
    except TypeError:
      return reader.peek() in terminators
  
  def append_text():
    nonlocal value
    value and values.append(TextNode(value))
    value = ''
  
  while len(reader) and not isterminated():
    if reader.is_line_start and reader.peeks('=', no_eof=False):
      append_text()
      values.append(parse_heading(reader))
    
    elif reader.is_line_start and reader.peeks(':', no_eof=False):
      append_text()
      values.append(parse_indent(reader))
    
    elif reader.is_line_start and reader.peeks('*', no_eof=False):
      append_text()
      values.append(parse_unordered_list(reader))
    
    elif reader.peeks("''", no_eof=False):
      append_text()
      values.append(parse_formatting(reader))
    
    elif reader.peeks('<', no_eof=False):
      try:
        html_ast = parse_html(reader)
        append_text()
        values.append(html_ast)
      except (ParserError, EOFError):
        value += reader.next()
    
    elif reader.peeks('[[', no_eof=False):
      append_text()
      values.append(parse_link(reader))
    
    elif reader.peeks('{{', no_eof=False):
      append_text()
      values.append(parse_braces(reader))
    
    elif reader.peeks('[', no_eof=False):
      try:
        with reader.consumer() as consumer:
          try:
            defref_ast = parse_defref(consumer)
            append_text()
            values.append(defref_ast)
          except SkipNode:
            pass
      except ParserError:
        value += reader.next()
    
    elif reader.consume('\n'):
      append_text()
      values.append(NewlineNode())
    
    else:
      value += reader.next()
  
  if no_eof and not isterminated():
    raise EOFError()
  
  append_text()
  return trim_text_nodes(values, mode=strip)

def parse_indent(reader: SourceReader) -> IndentNode:
  if not reader.is_line_start:
    raise ParserError('Indentation must be specified at line start', reader)
  if not reader.peeks(':'):
    raise ParserError(f'Unexpected character "{reader.peek()}", expected ":" (indentation)', reader)
  
  count = 0
  while reader.consume(':'):
    consume_whitespace(reader)
    count += 1
  
  return IndentNode(count)

def parse_braces(reader: SourceReader) -> BracesNode:
  try:
    with reader.consumer() as consumer:
      return parse_variable(consumer)
  except ParserError:
    pass
  
  if is_function(reader):
    return parse_function(reader)
  
  try:
    with reader.consumer() as consumer:
      return parse_template(consumer)
  except ParserError:
    raise ParserError('failed to parse braces', reader)

def parse_formatting(reader: SourceReader) -> ASTList:
  if reader.consume("'''''"):
    node = AST('bold', [AST('italic', [reader.consume_until("'")])])
    if not reader.consume("'''''"):
      raise ParserError("Expected \"'''''\" (end of bold & italic formatting)", reader)
  
  elif reader.consume("'''"):
    node = AST('bold', [reader.consume_until("'")])
    if not reader.consume("'''"):
      raise ParserError("Expected \"'''\" (end of bold formatting)", reader)
  
  elif reader.consume("''"):
    node = AST('italic', [reader.consume_until("'")])
    if not reader.consume("''"):
      raise ParserError("Expected \"''\" (end of italic formatting)", reader)
  
  else:
    raise ParserError(f"Unexpected \"{reader.peek()}\", expected \"'\" (start of formatting)", reader)
  
  return node

def parse_link(reader: SourceReader) -> LinkNode:
  if not reader.consume('[['):
    raise ParserError('Expected "[[" (start of link)', reader)
  
  url = parse_text(reader, terminators='|]')
  if reader.consume('|'):
    label = parse_text(reader, terminators=lambda r: r.peeks(']]'))
  else:
    label = url
  
  if not reader.consume(']]'):
    raise ParserError(f'Unexpected character "{reader.peek()}", expected "|" or "]]"', reader)
  
  return LinkNode(label, url)

def parse_html(reader: SourceReader) -> AST:
  # special HTML tags
  if reader.consume('<!--'):
    while reader.peeks('-'):
      reader.next()
    consume_whitespace(reader)
    
    content = ''
    while not reader.consume('-->'):
      content += reader.next()
    content = content.rstrip(' -')
    
    return CommentNode(content)
  
  if consume_selfclosing_tag(reader, 'nowiki'):
    return NoWikiNode()
  
  if consume_opentag(reader, 'nowiki'):
    s = ''
    while not consume_closetag(reader, 'nowiki'):
      s += reader.next()
    return NoWikiNode(s)
  
  if tag := consume_any_opentag(reader, ('noinclude', 'onlyinclude', 'includeonly')):
    def terminator(reader: SourceReader):
      return consume_closetag(reader.copy(), tag)
    contents = parse_text(reader, terminators=terminator)
    consume_closetag(reader, tag)
    return AST(tag, contents)
  
  if consume_opentag(reader, 'b'):
    def terminator(r: SourceReader):
      return consume_closetag(r, 'b')
    content = parse_text(reader, terminators=terminator)
    consume_closetag(reader, 'b')
    return FormatNode('bold', content)
  
  if consume_opentag(reader, 'i'):
    def terminator(r: SourceReader):
      return consume_closetag(r, 'i')
    content = parse_text(reader, terminators=terminator)
    return FormatNode('italic', content)
  
  if consume_opentag(reader, 'u'):
    def terminator(r: SourceReader):
      return consume_closetag(r, 'u')
    content = parse_text(reader, terminators=terminator)
    return FormatNode('underline', content)
  
  if consume_opentag(reader, 'br') or consume_selfclosing_tag(reader, 'br'):
    return LineBreakNode()
  
  return parse_generic_html(reader)

def parse_generic_html(reader: SourceReader) -> HTMLNode:
  with reader.consumer() as consumer:
    consume_whitespace(consumer)
    if not consumer.consume('<'):
      raise ParserError('Expected "<" (start of HTML tag)', consumer)
    consume_whitespace(consumer)
    if consumer.consume('/'):
      raise ParserError('Orphaned closing tag', consumer)
    
    tag = _parse_generic_html_tagname(consumer)
    attribs = []
    
    consume_whitespace(consumer)
    while not consumer.peek() in '/>':
      attribs.append(_parse_generic_html_attribute(consumer))
      consume_whitespace(consumer)
    
    if consumer.consume('/'):
      consume_whitespace(consumer)
      if not consumer.consume('>'):
        raise ParserError(f'Unexpected character "{consumer.peek()}", expected ">" (end of HTML tag)', consumer)
      return HTMLNode(tag, attribs, [])
      
    else:
      if not consumer.consume('>'):
        raise ParserError(f'Unexpected character "{consumer.peek()}", expected ">" (end of HTML tag)', consumer)
      
      def isterminated(r: SourceReader):
        return consume_closetag(r.copy(), tag)
      
      with consumer.consumer() as consumer2:
        contents = parse_text(consumer2, terminators=isterminated)
        if not consume_closetag(consumer2, tag):
          consumer2.revert()
          contents = []
      
      return HTMLNode(tag, attribs, contents)

def _parse_generic_html_tagname(reader: SourceReader) -> str:
  tag = ''
  
  consume_whitespace(reader)
  if reader.consume(':'):
    tag += ':'
  
  if not (c := reader.next()).isalpha():
    raise ParserError(f'Unexpected character "{c}", expected tagname', reader)
  
  tag += c
  while not reader.peek().isspace() and reader.peek() not in '/>':
    c = reader.next()
    if not c.isalnum() and c not in '-_:':
      raise ParserError(f'Unexpected character "{c}", expected tagname', reader)
    tag += c
  return tag

def _parse_generic_html_attribute(reader: SourceReader) -> HTMLAttributeNode:
  attr = _parse_generic_html_attribute_name(reader)
  consume_whitespace(reader)
  
  if reader.consume('='):
    consume_whitespace(reader)
    value = _parse_generic_html_attribute_value(reader)
  else:
    value = None
  
  return HTMLAttributeNode(attr, value)

def _parse_generic_html_attribute_name(reader: SourceReader) -> List[TextNode | BracesNode]:
  result = []
  txt = ''
  
  consume_whitespace(reader)
  if reader.consume(':'):
    txt += ':'
  
  if not (c := reader.next()).isalpha():
    raise ParserError(f'Unexpected character "{c}", expected attribute name', reader)
  txt += c
  
  def append_text():
    nonlocal txt
    txt.strip() and result.append(TextNode(txt))
    txt = ''
  
  while not reader.peek().isspace() and reader.peek() not in '=/>':
    if reader.peeks('{{'):
      append_text()
      result.append(parse_braces(reader))
    else:
      c = reader.next()
      
      if not c.isalnum() and not c in '-_:':
        raise ParserError(f'Unexpected character "{c}", expected attribute name', reader)
      txt += c
  
  append_text()
  return trim_text_nodes(result)

def _parse_generic_html_attribute_value(reader: SourceReader) -> List[AST]:
  if not reader.consume('"'):
    raise ParserError(f'Unexpected character "{reader.peek()}", expected """ (start of HTML attribute value)', reader)
  
  result = []
  txt = ''
  
  while not reader.peeks('"'):
    if reader.peeks('{{'):
      txt and result.append(TextNode(txt))
      txt = ''
      result.append(parse_braces(reader))
    elif reader.consume('\\'):
      txt += reader.next()
    else:
      txt += reader.next()
  
  txt and result.append(TextNode(txt))
  
  if not reader.consume('"'):
    raise ParserError(f'Unexpected character "{reader.peek()}", expected """ (end of HTML attribute value)', reader)
  return result

def parse_defref(reader: SourceReader) -> AST:
  """DefRef (definition reference) is a special node unique to this parser.
  It is not part of the standard specification. Similarly, the usage of
  the syntax parsed here is unique in usage to Wiktionary.
  
  The syntax follows the patterns `[<defnum><subdef>?]`,
  `[<defnum>, <defnum>, ...]`, `[<defnum>-<defnum>]`, and any mixture
  of these. It may also use `[*]` to designate *all* definitions.
  """
  # special case: all definitions
  if reader.consume('[*]'):
    return DefRefNode(['*'])
  if reader.consume('[?]'):
    raise SkipNode()
  
  if not reader.consume('['):
    raise ParserError(f'Unexpected character "{reader.peek()}", expected "[" (start of defref)', reader)
  
  ids = parse_defref_ids(reader)
  if not reader.consume(']'):
    raise ParserError(f'Unexpected character "{reader.peek()}", expected "]" (end of defref)', reader)
  return DefRefNode(ids)

def parse_defref_ids(reader: SourceReader) -> List[int]:
  """Parse a defref's IDs, which resemble a list of comma-separated
  individual bullets (@see `parse_defref_id`)."""
  consume_whitespace(reader)
  ids = set(parse_defref_id(reader))
  consume_whitespace(reader)
  
  while reader.consume(','):
    consume_whitespace(reader)
    ids = ids.union(parse_defref_id(reader))
    consume_whitespace(reader)
  
  return list(sorted(ids))

def parse_defref_id(reader: SourceReader) -> List[str]:
  """Parse a single defref id, which may be an integer, an
  integer with a lower-case letter, or a range of two integers."""
  lower = parse_int(reader)
  
  if reader.peek().isalpha():
    letter = reader.next()
    return [f"{lower}{letter}"]
  
  try:
    with reader.consumer() as consumer:
      consume_whitespace(consumer)
      if not consumer.consume('-') and not consumer.consume('–'):
        raise ParserError('Expected defnum range', reader)
      consume_whitespace(consumer)
      
      upper = parse_int(consumer)
      return list(map(str, range(lower, upper + 1)))
  except ParserError:
    return [str(lower)]

def parse_int(reader: SourceReader) -> int:
  """Parse a simple integer and return it w/o AST."""
  if not reader.peek().isdigit():
    raise ParserError(f'Expected integer, got "{reader.peek()}"', reader)
  
  i = 0
  n = 0
  while reader.peek().isdigit():
    i += int(reader.next()) * 10**n
    n += 1
  return i

def parse_unordered_list(reader: SourceReader) -> ListNode:
  items = []
  
  while True:
    items.append(parse_unordered_list_item(reader))
    
    try:
      consume_trailing_space(reader)
    except EOFError:
      break
    
    consume_blanklines(reader)
    if not reader.peeks('*', no_eof=False):
      break
  
  return ListNode(False, items)

def parse_unordered_list_item(reader: SourceReader) -> ListItemNode:
  if not reader.is_line_start:
    raise ParserError('List items must be placed on a new line', reader)
  
  consume_whitespace(reader)
  if not reader.peeks('*'):
    raise ParserError(f'Unexpected character "{reader.peek()}", expected "*" (start of list item)', reader)
  
  def terminator(r: SourceReader):
    return len(r) == 0 or r.peeks('\n')
  
  depth = consume_count(reader, '*')
  consume_whitespace(reader)
  content = parse_text(reader, terminators=terminator, strip='both')
  return ListItemNode(depth, content)


def consume_any(reader: SourceReader, choices: Collection[str]) -> str | None:
  for choice in choices:
    if reader.consume(choice):
      return choice
  return None

def consume_count(reader: SourceReader, c: str) -> int:
  count = 0
  while reader.consume(c):
    count += 1
  return count

def consume_whitespace(reader: SourceReader) -> bool:
  """Consumes an arbitrary number of whitespaces, including none. Returns True if any whitespace was consumed. Does not consume newlines."""
  consumed_any = False
  try:
    while reader.peek() in ' \t':
      reader.skip()
      consumed_any = True
  except EOFError:
    pass
  return consumed_any

def consume_any_whitespace(reader: SourceReader) -> bool:
  """Consumes any whitespaces, vertical and horizontal alike."""
  while len(reader) and reader.peek().isspace():
    reader.skip()

def consume_heading_space(reader: SourceReader):
  """Consumes heading space excluding newlines ahead of any non-whitespace character."""
  while len(reader) and reader.peek() in ' \t':
    reader.skip(1)

def consume_trailing_space(reader: SourceReader):
  """Consumes trailing space with a single newline."""
  while (c := reader.next()) != '\n':
    if not c.isspace():
      raise ParserError(f'Unexpected character {c}, expected arbitrary whitespace and/or newline', reader)

def consume_blanklines(reader: SourceReader):
  """Consumes blank lines, including none."""
  consumed_one = False
  while consume_blankline(reader):
    consumed_one = True
  return consumed_one

def consume_blankline(reader: SourceReader) -> bool:
  """Consumes a single blank line, including none. Returns True if a line was consumed, otherwise False."""
  consume_whitespace(reader)
  return reader.consume('\n')

def consume_opentag(reader: SourceReader, tag: str) -> bool:
  """Consumes an open tag, including the leading '<', trailing '>', and
  optional whitespaces. Returns True if the tag was consumed, otherwise False."""
  copy = reader.copy()
  
  if not copy.consume('<'):
    return False
  consume_whitespace(copy)
  if not copy.consume(tag, False):
    return False
  consume_whitespace(copy)
  if not copy.consume('>'):
    return False
  
  reader.skip(len(reader) - len(copy))
  return True

def consume_any_opentag(reader: SourceReader, tags: Sequence[str]) -> str | None:
  for tag in tags:
    if consume_opentag(reader, tag):
      return tag
  return None

def consume_closetag(reader: SourceReader, tag: str) -> bool:
  """Consumes a close tag, including the leading '</', trailing '>', and
  optional whitespaces. Returns True if the tag was consumed, otherwise False."""
  with reader.consumer() as consumer:
    if not consumer.consume('<'):
      consumer.revert()
      return False
    consume_whitespace(consumer)
    if not consumer.consume('/'):
      consumer.revert()
      return False
    consume_whitespace(consumer)
    if not consumer.consume(tag, False):
      consumer.revert()
      return False
    consume_whitespace(consumer)
    if not consumer.consume('>'):
      consumer.revert()
      return False
  return True

def consume_selfclosing_tag(reader: SourceReader, tag: str) -> bool:
  """Consumes a self-closing tag, including the leading '<', trailing '/>',
  and optional whitespaces. Returns True if the tag was consumed, otherwise False."""
  copy = reader.copy()
  
  if not copy.consume('<'):
    return False
  consume_whitespace(copy)
  if not copy.consume(tag, False):
    return False
  consume_whitespace(copy)
  if not copy.consume('/'):
    return False
  consume_whitespace(copy)
  if not copy.consume('>'):
    return False
  
  reader.skip(len(reader) - len(copy))
  return True

def consume_pipe(reader: SourceReader, *, optional = False):
  with reader.consumer() as consumer:
    consume_any_whitespace(consumer)
    if not consumer.consume('|'):
      if not optional:
        raise ParserError('Expected | (pipe)', consumer)
      else:
        consumer.revert()
        return False
    consume_any_whitespace(consumer)
    return True

def consume_tpl_close(reader: SourceReader, *, optional = False):
  with reader.consumer() as consumer:
    consume_any_whitespace(consumer)
    if not consumer.consume('}}'):
      if not optional:
        raise ParserError('Expected }} (end of template/parser function)', reader)
      else:
        consumer.revert()
        return False
  return True

def consume_invoke(reader: SourceReader):
  with reader.consumer() as consumer:
    consume_any_whitespace(consumer)
    if not consumer.consume('#'):
      consumer.revert()
      return False
    
    consume_any_whitespace(consumer)
    if not consumer.consume('invoke:'):
      consumer.revert()
      return False
    return True

def tplterm(reader: SourceReader):
  return reader.peeks('|') or reader.peeks('}}')

def trim_text_nodes(ast: Iterable[AST], mode: Literal['none', 'both', 'left', 'right'] = 'both') -> List[AST]:
  """Trims first level text nodes from the given AST node sequence.
  If a trimmed text node is empty, it's removed from the resulting list entirely.
  
  The first text node will be trimmed only from the left when requested. The last text node will be trimmed only from
  the right when requested."""
  result = list(ast)
  
  if mode in ('left', 'both'):
    while len(result) and result[0].name == 'text' and result[0].children[0][0].isspace():
      result[0].children = (result[0].children[0].lstrip(),)
      if not result[0].children[0]:
        result = result[1:]
  
  if mode in ('right', 'both'):
    while len(result) and result[-1].name == 'text' and result[-1].children[0][-1].isspace():
      result[-1].children = (result[-1].children[0].rstrip(),)
      if not result[-1].children[0]:
        result = result[:-1]
  
  return result
