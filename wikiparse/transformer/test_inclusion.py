from .inclusion import InclusionTransformer
from ..ast import *
import pytest

@pytest.mark.asyncio
async def test_identity():
  tf = InclusionTransformer()
  ast = [TextNode('foo'), TemplateNode('bar', [PosArgNode('baz')], []), TextNode('bork')]
  assert await tf.matches(ast)
  assert await tf.transform(ast, dict()) == ast

@pytest.mark.asyncio
async def test_noinclude():
  tf = InclusionTransformer()
  ast = [TextNode('foo'), NoIncludeNode([TextNode('removed')])]
  assert await tf.matches(ast)
  assert await tf.transform(ast, dict()) == [TextNode('foo')]

@pytest.mark.asyncio
async def test_onlyinclude():
  tf = InclusionTransformer()
  ast = [OnlyIncludeNode([TextNode('first')]), TextNode('removed'), OnlyIncludeNode([TextNode('second')])]
  assert await tf.matches(ast)
  assert await tf.transform(ast, dict()) == [TextNode('first'), TextNode('second')]
