from __future__ import annotations
from typing import *

from wikiparse.renderer.identifier import IdentifierRenderer

from ..ast import AST, ASTList, NamedArgNode, PosArgNode, TemplateNode, VariableNode
from ..utils import isiterable, iterable
from .transformer import Transformer, Variables
from .inclusion import InclusionTransformer

identifier_renderer = IdentifierRenderer()
inclusion_transformer = InclusionTransformer()

class Transcluder(Transformer):
  def __init__(self, fetch_template: FetchTemplate):
    self.fetch_template = fetch_template
    self.identifier_renderer = identifier_renderer
  
  async def transform(self, ast: ASTList, vars: Variables) -> ASTList:
    if not vars:
      vars = dict()
    
    if isiterable(ast) and type(ast) is not str:
      result = []
      for node in ast:
        transcluded = await self.transform(node, vars)
        if type(transcluded) is unit:
          result.extend(transcluded.ast)
        else:
          result.append(transcluded)
      return result
    
    elif AST.isastlike(ast):
      fn = f'_transclude_{ast.name}'
      if hasattr(self, fn):
        return await getattr(self, fn)(ast, vars)
      else:
        ast.children = await self.transform(ast.children, vars)
        return ast
    
    else:
      return ast
  
  async def _transclude_template(self, tpl: TemplateNode, vars: Variables) -> ASTList:
    name, posargs, namedargs = await self.transform(tpl.children, vars)
    ast = await self.fetch_template(renderid(name))
    vars = self.make_vars(posargs, namedargs)
    return unit(iterable(await transclude_inclusion(await self.transform(ast, vars))))
  
  async def _transclude_variable(self, var: VariableNode, vars: Variables) -> ASTList:
    name, default = var.children
    name = renderid(name)
    print(vars[name])
    return unit(iterable(vars[name] if name in vars else default))
  
  def make_vars(self, posargs: Sequence[PosArgNode], namedargs: Sequence[NamedArgNode]) -> Variables:
    result = dict()
    for i, posarg in enumerate(posargs):
      result[str(i+1)] = posarg.children[0]
    for namedarg in namedargs:
      name, val = namedarg.children
      result[self.render(name)] = val
    return result

class unit:
  """Simple wrapper around a `List[AST]` with the semantics that
  interpreting code should flatten instances into an encapsulating list."""
  def __init__(self, ast: List[AST]):
    self.ast = ast

def renderid(ast: ASTList) -> str:
  return identifier_renderer.render(ast)

async def transclude_inclusion(ast: ASTList) -> ASTList:
  return await inclusion_transformer.transform(ast, dict())

FetchTemplate = Callable[[str], Awaitable[ASTList]]
