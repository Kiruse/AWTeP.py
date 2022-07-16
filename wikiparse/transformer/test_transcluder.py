from wikiparse.renderer.html import HTMLRenderer
from ..ast import *
from .transcluder import Transcluder, TranscluderAPI
import pytest

class API(TranscluderAPI):
  def __init__(self):
    self.renderer = HTMLRenderer()
  
  async def fetch_template(self, name: str) -> ASTList:
    if name == 'foo':
      return [TextNode('foo')]
    if name == 'nested':
      return [TemplateNode('foo', [], [])]
    if name == 'with-var':
      return [VariableNode('1', None)]
  
  async def page_exists(self, name: str) -> bool:
    return name in ('foo', 'nested', 'with-var')
  
  def render(self, ast: ASTList) -> str:
    return self.renderer.render(ast)
  
  def renderid(self, ast: ASTList) -> str:
    return self.render(ast)

@pytest.mark.asyncio
async def test_identity():
  tf = Transcluder(API())
  ast = [TextNode('foo'), TextNode('bar')]
  assert await tf.matches(ast)
  assert await tf.transform(ast, dict()) == ast

@pytest.mark.asyncio
async def test_simple_template():
  tf = Transcluder(API())
  ast = [TextNode('foo'), TemplateNode('foo', [], [])]
  assert await tf.matches(ast)
  assert await tf.transform(ast, dict()) == [TextNode('foo'), TextNode('foo')]

@pytest.mark.asyncio
async def test_template_with_var():
  tf = Transcluder(API())
  ast = [TemplateNode('with-var', [PosArgNode([TextNode('foo')])], [])]
  assert await tf.matches(ast)
  assert await tf.transform(ast, dict()) == [TextNode('foo')]

@pytest.mark.asyncio
async def test_nested_template():
  tf = Transcluder(API())
  ast = [TemplateNode('nested', [], [])]
  assert await tf.matches(ast)
  assert await tf.transform(ast, dict()) == [TextNode('foo')]

@pytest.mark.asyncio
async def test_evaluate_if():
  tf = Transcluder(API())
  ast = [IfNode([TextNode('foo')], [TextNode('true')], [TextNode('false')])]
  assert await tf.matches(ast)
  assert await tf.transform(ast, dict()) == [TextNode('true')]
  
  tf = Transcluder(API())
  ast = [IfNode([TextNode('')], [TextNode('true')], [TextNode('false')])]
  assert await tf.matches(ast)
  assert await tf.transform(ast, dict()) == [TextNode('false')]
  
  tf = Transcluder(API())
  ast = [IfNode([TextNode(' ')], [TextNode('true')], [TextNode('false')])]
  assert await tf.matches(ast)
  assert await tf.transform(ast, dict()) == [TextNode('false')]

@pytest.mark.asyncio
async def test_evaluate_ifeq():
  tf = Transcluder(API())
  ast = [IfEqNode([TextNode('lhs')], [TextNode('rhs')], [TextNode('true')], [TextNode('false')])]
  assert await tf.matches(ast)
  assert await tf.transform(ast, dict()) == [TextNode('false')]
  
  tf = Transcluder(API())
  ast = [IfEqNode([TextNode('val')], [TextNode('val')], [TextNode('true')], [TextNode('false')])]
  assert await tf.matches(ast)
  assert await tf.transform(ast, dict()) == [TextNode('true')]
  
  tf = Transcluder(API())
  ast = [IfEqNode([TextNode('val ')], [TextNode(' val')], [TextNode('true')], [TextNode('false')])]
  assert await tf.matches(ast)
  assert await tf.transform(ast, dict()) == [TextNode('true')]
  
  tf = Transcluder(API())
  ast = [IfEqNode([TextNode('')], [TextNode('val')], [TextNode('true')], [TextNode('false')])]
  assert await tf.matches(ast)
  assert await tf.transform(ast, dict()) == [TextNode('false')]

@pytest.mark.asyncio
async def test_evaluate_ifexist():
  tf = Transcluder(API())
  ast = [IfExistNode([TextNode('foo')], [TextNode('true')], [TextNode('false')])]
  assert await tf.matches(ast)
  assert await tf.transform(ast, dict()) == [TextNode('true')]
  
  tf = Transcluder(API())
  ast = [IfExistNode([TextNode('nonexistent')], [TextNode('true')], [TextNode('false')])]
  assert await tf.matches(ast)
  assert await tf.transform(ast, dict()) == [TextNode('false')]
