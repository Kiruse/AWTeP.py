from ..ast import *
from .transcluder import Transcluder
import pytest

async def fetch_dummy(name: str) -> ASTList:
  if name == 'foo':
    return [TextNode('foo')]
  if name == 'nested':
    return [TemplateNode('foo', [], [])]
  if name == 'with-var':
    return [VariableNode('1', None)]

@pytest.mark.asyncio
async def test_identity():
  tf = Transcluder(fetch_dummy)
  ast = [TextNode('foo'), TextNode('bar')]
  assert await tf.matches(ast)
  assert await tf.transform(ast, dict()) == ast

@pytest.mark.asyncio
async def test_simple_template():
  tf = Transcluder(fetch_dummy)
  ast = [TextNode('foo'), TemplateNode('foo', [], [])]
  assert await tf.matches(ast)
  assert await tf.transform(ast, dict()) == [TextNode('foo'), TextNode('foo')]

@pytest.mark.asyncio
async def test_template_with_var():
  tf = Transcluder(fetch_dummy)
  ast = [TemplateNode('with-var', [PosArgNode([TextNode('foo')])], [])]
  assert await tf.matches(ast)
  assert await tf.transform(ast, dict()) == [TextNode('foo')]

@pytest.mark.asyncio
async def test_nested_template():
  tf = Transcluder(fetch_dummy)
  ast = [TemplateNode('nested', [], [])]
  assert await tf.matches(ast)
  assert await tf.transform(ast, dict()) == [TextNode('foo')]
