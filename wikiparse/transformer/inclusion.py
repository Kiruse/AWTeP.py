from __future__ import annotations
from typing import *

from ..ast import AST, ASTList, OnlyIncludeNode
from ..utils import NotFound, isiterable
from .transformer import Transformer, Variables

class InclusionTransformer(Transformer):
  """A transformer to transform an AST for transclusion within another.
  
  If the given AST contains an <onlyinclude> tag, only its contents
  will be transcluded. Multiple such tags may exist, in which case
  all such tags are treated as siblings and transcluded in order.
  
  If no such <onlyinclude> tag is found, the transformer respects the
  <noinclude> and <includeonly> tags which omit their contents from
  transclusion or direct page rendering, respectively. Any AST outside
  these tags is transcluded and/or rendered anyways.
  
  **Note** that this transformer should be called after transclusion
  of the provided AST but before transclusion within another AST. This
  is because the <onlyinclude> algorithm promotes any and all tags
  regardless of context, such as evaluating parser functions.
  """
  async def transform(self, ast: ASTList, _: Variables) -> ASTList:
    if (only := self.find_onlyinclude(ast)) is not NotFound:
      result: List[AST] = []
      for node in only:
        result.extend(node.children)
      return result
    return self.strip_noinclude(ast)
  
  def find_onlyinclude(self, ast: ASTList) -> List[OnlyIncludeNode] | NotFound:
    if isiterable(ast) and type(ast) is not str:
      result: List[OnlyIncludeNode] = []
      for node in ast:
        curr = self.find_onlyinclude(node)
        if curr is not NotFound:
          result.extend(curr)
      return result if len(result) else NotFound
    
    if AST.isastlike(ast):
      return (ast,) if ast.name == 'onlyinclude' else self.find_onlyinclude(ast.children)
    
    return NotFound
  
  def strip_noinclude(self, ast: ASTList) -> ASTList:
    if isiterable(ast) and type(ast) is not str:
      ast = list(filter(lambda n: not AST.isastlike(n) or n.name != 'noinclude', ast))
      for node in ast:
        self.strip_noinclude(node)
      return ast
    if AST.isastlike(ast):
      ast.children = self.strip_noinclude(ast.children)
      return ast
    return ast
