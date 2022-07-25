from __future__ import annotations
from typing import *
from ..ast import ASTList, NamedArgNode, PosArgNode
from ..wikipage import WikiPage

class Transformer:
  async def matches(self, ast: ASTList) -> bool:
    return True
  
  async def transform(self, ast: WikiPage | ASTList, vars: Variables, page: WikiPage | None) -> ASTList:
    raise NotImplementedError()

def make_vars(render: Callable[[ASTList], str], posargs: Sequence[PosArgNode], namedargs: Sequence[NamedArgNode]) -> Variables:
  result = dict()
  for i, posarg in enumerate(posargs):
    result[str(i+1)] = posarg.children[0]
  for namedarg in namedargs:
    name, val = namedarg.children
    result[render(name)] = val
  return result

Variables = Dict[str, ASTList]
