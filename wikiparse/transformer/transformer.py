from __future__ import annotations
from typing import *
from ..ast import ASTList

class Transformer:
  async def matches(self, ast: ASTList) -> bool:
    return True
  
  async def transform(self, ast: ASTList, vars: Variables) -> ASTList:
    raise NotImplementedError()

Variables = Dict[str, ASTList]
