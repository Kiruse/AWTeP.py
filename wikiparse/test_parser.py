from typing import *
from .source_reader import SourceReader
from .parser import *
from .ast import *
from .error import ParserError, RedirectError
import pytest

def test_parse_directive():
  source = SourceReader('# redirect [[foo]]')
  with pytest.raises(RedirectError, match=r'redirects to \[text\([\'"]foo[\'"]\)\]'):
    parse_directive(source)
  
  source = SourceReader('# WeiTerLeiTung [[bar]]', 'foo')
  with pytest.raises(RedirectError, match=r'foo redirects to \[text\([\'"]bar[\'"]\)\]'):
    parse_directive(source)

def test_parse_heading():
  reader = SourceReader('= H1 =\n')
  assert parse_heading(reader) == HeadingNode([TextNode('H1')], 1)
  
  reader = SourceReader('== H2 ==\n')
  assert parse_heading(reader) == HeadingNode([TextNode('H2')], 2)
  
  reader = SourceReader('=== H3 ===\n')
  assert parse_heading(reader) == HeadingNode([TextNode('H3')], 3)
  
  reader = SourceReader('==== H4 ====\n')
  assert parse_heading(reader) == HeadingNode([TextNode('H4')], 4)
  
  reader = SourceReader('===== H5 =====\n')
  assert parse_heading(reader) == HeadingNode([TextNode('H5')], 5)
  
  reader = SourceReader('====== H6 ======\n')
  assert parse_heading(reader) == HeadingNode([TextNode('H6')], 6)
  
  with pytest.raises(ParserError):
    reader = SourceReader('= heading ==\n')
    parse_heading(reader)
  
  with pytest.raises(ParserError):
    reader = SourceReader('== heading =\n')
    parse_heading(reader)
  
  with pytest.raises(ParserError):
    reader = SourceReader('{{Fake}}\n')
    parse_heading(reader)
  
  with pytest.raises(ParserError):
    reader = SourceReader('not a heading\n')
    parse_heading(reader)

def test_parse_template():
  reader = SourceReader('{{Template}}')
  assert parse_template(reader) == TemplateNode([TextNode('Template')], [], [])
  
  reader = SourceReader('{{Foo}}')
  assert parse_template(reader) == TemplateNode([TextNode('Foo')], [], [])
  
  reader = SourceReader('{{Foo|bar}}')
  assert parse_template(reader) == TemplateNode([TextNode('Foo')], [PosArgNode([TextNode('bar')])], [])
  
  reader = SourceReader('{{Foo|bar|baz}}')
  assert parse_template(reader) == TemplateNode([TextNode('Foo')], [PosArgNode([TextNode('bar')]), PosArgNode([TextNode('baz')])], [])
  
  reader = SourceReader('{{Foo|bar=baz}}')
  assert parse_template(reader) == TemplateNode([TextNode('Foo')], [], [NamedArgNode([TextNode('bar')], [TextNode('baz')])])
  
  reader = SourceReader('{{Foo|bar=bar|baz=baz|quux=quux}}')
  assert parse_template(reader) == TemplateNode([TextNode('Foo')], [], [NamedArgNode([TextNode('bar')], [TextNode('bar')]), NamedArgNode([TextNode('baz')], [TextNode('baz')]), NamedArgNode([TextNode('quux')], [TextNode('quux')])])
  
  reader = SourceReader('{{Foo|bar|baz|quux=quux}}')
  assert parse_template(reader) == TemplateNode([TextNode('Foo')], [PosArgNode([TextNode('bar')]), PosArgNode([TextNode('baz')])], [NamedArgNode([TextNode('quux')], [TextNode('quux')])])
  
  reader = SourceReader('{{Foo|bar|baz=baz|quux}}')
  assert parse_template(reader) == TemplateNode([TextNode('Foo')], [PosArgNode([TextNode('bar')]), PosArgNode([TextNode('quux')])], [NamedArgNode([TextNode('baz')], [TextNode('baz')])])
  
  reader = SourceReader('{{Foo | bar | baz = baz | quux }}')
  assert parse_template(reader) == TemplateNode([TextNode('Foo')], [PosArgNode([TextNode('bar')]), PosArgNode([TextNode('quux')])], [NamedArgNode([TextNode('baz')], [TextNode('baz')])])
  
  reader = SourceReader('{{{{{foo}}}|bar}}')
  assert parse_template(reader) == TemplateNode([VariableNode([TextNode('foo')], None)], [PosArgNode([TextNode('bar')])], [])
  
  reader = SourceReader('{{{{{1|}}}}}')
  assert parse_template(reader) == TemplateNode([VariableNode([TextNode('1')], [])], [], [])
  
  reader = SourceReader('{{{{foo}}}}')
  assert parse_template(reader) == TemplateNode([TemplateNode([TextNode('foo')], [], [])], [], [])
  
  reader = SourceReader('{{{{{1}}}}}')
  assert parse_template(reader) == TemplateNode([VariableNode([TextNode('1')], None)], [], [])

def test_parse_variable():
  source = SourceReader('{{{0}}}')
  assert parse_variable(source) == VariableNode([TextNode('0')], None)
  
  source = SourceReader('{{{foo}}}')
  assert parse_variable(source) == VariableNode([TextNode('foo')], None)
  
  source = SourceReader('{{{0|}}}')
  assert parse_variable(source) == VariableNode([TextNode('0')], [])
  
  source = SourceReader('{{{foo|bar}}}')
  assert parse_variable(source) == VariableNode([TextNode('foo')], [TextNode('bar')])
  
  source = SourceReader('{{{{{{0}}}}}}')
  assert parse_variable(source) == VariableNode([VariableNode([TextNode('0')], None)], None)
  
  source = SourceReader('{{{{{{0|}}}}}}')
  assert parse_variable(source) == VariableNode([VariableNode([TextNode('0')], [])], None)
  
  source = SourceReader('{{{{{{0}}}|}}}')
  assert parse_variable(source) == VariableNode([VariableNode([TextNode('0')], None)], [])
  
  # cannot nest a template in a variable identifier
  with pytest.raises(ParserError):
    source = SourceReader('{{{ {{foo}} }}}')
    parse_variable(source)

def test_parse_invoke():
  # NOTE: this is a special case of test_parse_template using the magic word '#invoke:'
  reader = SourceReader('{{#invoke:Module|Function|foo|bar|baz=quux}}')
  assert parse_function(reader) == InvokeNode(
    [TextNode('Module')],
    [TextNode('Function')],
    [PosArgNode([TextNode('foo')]), PosArgNode([TextNode('bar')])],
    [NamedArgNode([TextNode('baz')], [TextNode('quux')])],
  )
  
  reader = SourceReader('{{ # invoke: Foo | bar | baz = quux }}')
  assert parse_function(reader) == InvokeNode(
    [TextNode('Foo')],
    [TextNode('bar')],
    [],
    [NamedArgNode([TextNode('baz')], [TextNode('quux')])],
  )
  
  reader = SourceReader('{{#\ninvoke:Foo|bar|baz=quux}}')
  assert parse_function(reader) == InvokeNode(
    [TextNode('Foo')],
    [TextNode('bar')],
    [],
    [NamedArgNode([TextNode('baz')], [TextNode('quux')])],
  )

def test_parse_function_if():
  source = SourceReader('{{#if: text | true | false}}')
  assert parse_function(source) == IfNode([TextNode('text')], [TextNode('true')], [TextNode('false')])
  
  source = SourceReader('{{#if:text|true|false}}')
  assert parse_function(source) == IfNode([TextNode('text')], [TextNode('true')], [TextNode('false')])
  
  source = SourceReader('{{#if: {{{foo}}} | true | false }}')
  assert parse_function(source) == IfNode([VariableNode([TextNode('foo')], None)], [TextNode('true')], [TextNode('false')])

def test_parse_function_ifeq():
  source = SourceReader('{{#ifeq: lhs | rhs | true | false}}')
  assert parse_function(source) == IfEqNode([TextNode('lhs')], [TextNode('rhs')], [TextNode('true')], [TextNode('false')])
  
  source = SourceReader('{{#ifeq: {{{lhs}}} | {{{rhs}}} | true | false}}')
  assert parse_function(source) == IfEqNode([VariableNode([TextNode('lhs')], None)], [VariableNode([TextNode('rhs')], None)], [TextNode('true')], [TextNode('false')])

def test_parse_function_ifexist():
  source = SourceReader('{{#ifexist: Hund | true | false}}')
  assert parse_function(source) == IfExistNode([TextNode('Hund')], [TextNode('true')], [TextNode('false')])

def test_parse_function_switch():
  source = SourceReader('{{#switch: foo | foo = bar | #default = baz}}')
  assert parse_function(source) == SwitchNode([TextNode('foo')],
    [
      SwitchBranchNode([TextNode('foo')], [TextNode('bar')]),
      SwitchBranchNode([TextNode('#default')], [TextNode('baz')]),
    ])
  assert len(source) == 0
  
  source = SourceReader('{{#switch: foo | foo = bar | bar | baz | #default = quux}}')
  assert parse_function(source) == SwitchNode([TextNode('foo')],
    [
      SwitchBranchNode([TextNode('foo')], [TextNode('bar')]),
      SwitchBranchNode([TextNode('bar')], [TextNode('quux')]),
      SwitchBranchNode([TextNode('baz')], [TextNode('quux')]),
      SwitchBranchNode([TextNode('#default')], [TextNode('quux')]),
    ])
  assert len(source) == 0
  
  source = SourceReader('{{#switch: {{{1|}}}| foo = bar | #default = baz}}')
  assert parse_function(source) == SwitchNode([VariableNode([TextNode('1')], [])],
    [
      SwitchBranchNode([TextNode('foo')], [TextNode('bar')]),
      SwitchBranchNode([TextNode('#default')], [TextNode('baz')]),
    ])
  assert len(source) == 0
  
  source = SourceReader('{{#switch: {{{1|}}}| foo = bar | default value}}')
  assert parse_function(source) == SwitchNode([VariableNode([TextNode('1')], [])],
    [
      SwitchBranchNode([TextNode('foo')], [TextNode('bar')]),
      SwitchBranchNode([TextNode('#default')], [TextNode('default value')]),
    ])
  assert len(source) == 0
  
  source = SourceReader('{{#switch: {{{1|}}}| foo = bar | bar | default}}')
  assert parse_function(source) == SwitchNode([VariableNode([TextNode('1')], [])],
    [
      SwitchBranchNode([TextNode('foo')], [TextNode('bar')]),
      SwitchBranchNode([TextNode('bar')], [TextNode('default')]),
      SwitchBranchNode([TextNode('#default')], [TextNode('default')]),
    ])
  assert len(source) == 0

def test_parse_formatting():
  reader = SourceReader("''text''")
  assert parse_formatting(reader) == FormatNode('italic', ['text'])
  
  reader = SourceReader("'''text'''")
  assert parse_formatting(reader) == FormatNode('bold', ['text'])
  
  reader = SourceReader("'''''text'''''")
  assert parse_formatting(reader) == FormatNode('bold', [FormatNode('italic', ['text'])])
  
  with pytest.raises(ParserError):
    reader = SourceReader("'''text''")
    parse_formatting(reader)

def test_parse_link():
  reader = SourceReader('[[page]]')
  assert parse_link(reader) == LinkNode([TextNode('page')], [TextNode('page')])
  
  reader = SourceReader('[[page|Label]]')
  assert parse_link(reader) == LinkNode([TextNode('Label')], [TextNode('page')])

def test_parse_special_html():
  reader = SourceReader('<nowiki>text</nowiki>')
  assert parse_html(reader) == NoWikiNode('text')
  
  reader = SourceReader('<nowiki />')
  assert parse_html(reader) == NoWikiNode()
  
  reader = SourceReader('<nowiki/>')
  assert parse_html(reader) == NoWikiNode()
  
  reader = SourceReader('<b>bold text</b>')
  assert parse_html(reader) == FormatNode('bold', [TextNode('bold text')])
  
  reader = SourceReader('<b>bold<nowiki />text</b>')
  assert parse_html(reader) == FormatNode('bold', [TextNode('bold'), NoWikiNode(), TextNode('text')])
  
  reader = SourceReader('<i>italic text</i>')
  assert parse_html(reader) == AST('italic', [TextNode('italic text')])

def test_parse_generic_html():
  reader = SourceReader('<span>foo</span>')
  assert parse_html(reader) == HTMLNode('span', [], [TextNode('foo')])
  
  reader = SourceReader('< span > foo < / span >')
  assert parse_html(reader) == HTMLNode('span', [], [TextNode(' foo ')])
  
  reader = SourceReader('<span class="foo" id="some-id">foo</span>')
  assert parse_html(reader) == HTMLNode('span', [HTMLAttributeNode([TextNode('class')], [TextNode('foo')]), HTMLAttributeNode([TextNode('id')], [TextNode('some-id')])], [TextNode('foo')])
  
  reader = SourceReader('<foo>bar</foo>')
  assert parse_html(reader) == HTMLNode('foo', [], [TextNode('bar')])
  
  reader = SourceReader('<foo />')
  assert parse_html(reader) == HTMLNode('foo', [], [])
  
  reader = SourceReader('< foo / >')
  assert parse_html(reader) == HTMLNode('foo', [], [])
  
  # correctly identify non-HTML
  with pytest.raises(EOFError):
    reader = SourceReader('< foo')
    parse_html(reader)
  
  with pytest.raises(ParserError):
    reader = SourceReader('< b/2')
    parse_html(reader)
  
  reader = SourceReader('a < b')
  assert parse_text(reader, terminators=term_eof) == [TextNode('a < b')]

def test_parse_inclusion_tags():
  reader = SourceReader('<noinclude>not included during transclusion</noinclude>')
  assert parse_html(reader) == NoIncludeNode([TextNode('not included during transclusion')])
  
  reader = SourceReader('<onlyinclude>other content is excluded</onlyinclude>')
  assert parse_html(reader) == OnlyIncludeNode([TextNode('other content is excluded')])
  
  reader = SourceReader('<includeonly>only included, not rendered</includeonly>')
  assert parse_html(reader) == IncludeOnlyNode([TextNode('only included, not rendered')])
  
  reader = SourceReader('< noinclude >foo</ noinclude >')
  assert parse_html(reader) == NoIncludeNode([TextNode('foo')])

def test_parse_html_comment():
  reader = SourceReader('<!-- comment -->')
  assert parse_html(reader) == CommentNode('comment')
  
  reader = SourceReader('<!----- some comment --->')
  assert parse_html(reader) == CommentNode('some comment')
  
  reader = SourceReader('<!---comment--->')
  assert parse_html(reader) == CommentNode('comment')
  
  with pytest.raises(ParserError):
    reader = SourceReader('<! -- invalid -->')
    parse_html(reader)
  
  with pytest.raises(EOFError):
    reader = SourceReader('<!-- invalid -- >')
    parse_html(reader)

def test_parse_text():
  # Simple formatting & default terminators
  reader = SourceReader("foo 'bar' ''italic'' '''bold'''\nbaz")
  assert parse_text(reader) == [TextNode("foo 'bar' "), FormatNode('italic', ['italic']), TextNode(" "), FormatNode('bold', ['bold'])]
  assert reader.peek() == '\n'
  assert str(reader) == '\nbaz'
  
  # Does not raise EOFError
  reader = SourceReader('foo bar')
  assert parse_text(reader, no_eof=False) == [TextNode('foo bar')]
  
  # Raises EOFError
  with pytest.raises(EOFError):
    parse_text(SourceReader('foo bar'), no_eof=True)
  
  # Different Terminators
  reader = SourceReader('foo|bar')
  assert parse_text(reader, terminators='|') == [TextNode('foo')]
  assert reader.consume('|')
  with pytest.raises(EOFError):
    parse_text(reader.copy(), terminators='|', no_eof=True)
  assert parse_text(reader, terminators='|', no_eof=False) == [TextNode('bar')]
  
  # Parses links
  reader = SourceReader('[[page|title]]')
  assert parse_text(reader, no_eof=False) == [LinkNode([TextNode('title')], [TextNode('page')])]

def test_parse_indent():
  with pytest.raises(ParserError):
    reader = SourceReader('no indent')
    parse_indent(reader)
  
  reader = SourceReader(':level 1 indent')
  assert parse_indent(reader) == IndentNode(1)
  assert str(reader) == 'level 1 indent'
  
  reader = SourceReader('::level 2 indent')
  assert parse_indent(reader) == IndentNode(2)
  assert str(reader) == 'level 2 indent'
  
  reader = SourceReader(':::level 3 indent')
  assert parse_indent(reader) == IndentNode(3)
  assert str(reader) == 'level 3 indent'
  
  reader = SourceReader('\n  :indent with preceeding whitespace')
  ast = parse_text(reader, terminators=lambda r: len(r) == 0)
  assert ast == [TextNode('\n  '), IndentNode(1), TextNode('indent with preceeding whitespace')]

def test_parse_defref():
  # invalid cases
  with pytest.raises(ParserError):
    reader = SourceReader('[foo]')
    parse_defref(reader)
  
  # standard cases
  reader = SourceReader('[1]')
  assert parse_defref(reader) == DefRefNode(['1'])
  
  reader = SourceReader('[1, 2, 3]')
  assert parse_defref(reader) == DefRefNode(['1', '2', '3'])
  
  reader = SourceReader('[1, 3, 5]')
  assert parse_defref(reader) == DefRefNode(['1', '3', '5'])
  
  reader = SourceReader('[1, 5, 3]')
  assert parse_defref(reader) == DefRefNode(['1', '3', '5'])
  
  reader = SourceReader('[1-3]')
  assert parse_defref(reader) == DefRefNode(['1', '2', '3'])
  
  reader = SourceReader('[1-3, 4]')
  assert parse_defref(reader) == DefRefNode(['1', '2', '3', '4'])
  
  reader = SourceReader('[1-3, 4a, 4b]')
  assert parse_defref(reader) == DefRefNode(['1', '2', '3', '4a', '4b'])
  
  with pytest.raises(ParserError):
    reader = SourceReader('[1a-1c]')
    parse_defref(reader)
  
  # part of parse_text
  reader = SourceReader(':[1-3] foobar')
  assert parse_text(reader, terminators=term_eof) == [IndentNode(1), DefRefNode(['1', '2', '3']), TextNode(' foobar')]
  
  # special cases
  reader = SourceReader('[*]')
  assert parse_defref(reader) == DefRefNode(['*'])
  
  with pytest.raises(SkipNode):
    reader = SourceReader('[?]')
    parse_defref(reader)
  
  reader = SourceReader('foo [?] bar')
  assert parse_text(reader, terminators=term_eof) == [TextNode('foo  bar')]

def test_parse_unordered_list():
  # clean cases
  reader = SourceReader('* foo')
  assert parse_unordered_list(reader) == ListNode(False, [ListItemNode(1, [TextNode('foo')])])
  
  reader = SourceReader('* foo\n* bar\n* baz')
  assert parse_unordered_list(reader) == ListNode(False, [
    ListItemNode(1, [TextNode('foo')]),
    ListItemNode(1, [TextNode('bar')]),
    ListItemNode(1, [TextNode('baz')]),
  ])
  
  reader = SourceReader('* foo\n** bar\n*** baz\n* quux')
  assert parse_unordered_list(reader) == ListNode(False, [
    ListItemNode(1, [TextNode('foo')]),
    ListItemNode(2, [TextNode('bar')]),
    ListItemNode(3, [TextNode('baz')]),
    ListItemNode(1, [TextNode('quux')]),
  ])
  
  # dirty cases
  reader = SourceReader('  *foo \n *bar \n *baz')
  assert parse_unordered_list(reader) == ListNode(False, [
    ListItemNode(1, [TextNode('foo')]),
    ListItemNode(1, [TextNode('bar')]),
    ListItemNode(1, [TextNode('baz')]),
  ])
  
  reader = SourceReader(' * foo\n* *bar')
  assert parse_unordered_list(reader) == ListNode(False, [
    ListItemNode(1, [TextNode('foo')]),
    ListItemNode(1, [TextNode('*bar')]),
  ])
  
  # parse_text integration
  reader = SourceReader('\n*foo\n *bar')
  assert parse_text(reader, terminators=term_eof) == [TextNode('\n'), ListNode(False, [ListItemNode(1, [TextNode('foo')]), ListItemNode(1, [TextNode('bar')])])]

def test_parsetpl():
  assert parsetpl(src_tplfoo, "Vorlage:Foo") == ([], [TextNode("foo\nbar\nbaz")])
  
  assert parsetpl(src_tplbar, "Vorlage:Bar") == ([], [
    IfNode([VariableNode([TextNode('foo')], [])], [TextNode('bar')], [TextNode('baz')])
  ])

src_tplfoo = """
foo
bar
baz
"""

src_tplbar = """
{{#if: {{{foo|}}} | bar | baz }}
"""

def term_eof(r: SourceReader):
  return len(r) == 0
