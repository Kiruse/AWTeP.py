from ..parser import parse
from .html import HTMLRenderer

def test_simple():
  rndr = HTMLRenderer()
  ast = parse("''italic'''''bold'''")
  assert rndr.render(ast) == '<i>italic</i><b>bold</b>'

def test_attributes():
  rndr = HTMLRenderer()
  ast = parse('<div class="foo">bar</div>')
  assert rndr.render(ast) == '<div class="foo">bar</div>'

def test_nested():
  rndr = HTMLRenderer()
  ast = parse('<div>level 1A<div>level 2</div>level 1B</div>')
  assert rndr.render(ast) == '<div>level 1A<div>level 2</div>level 1B</div>'
