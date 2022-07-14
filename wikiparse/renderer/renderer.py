from __future__ import annotations
from typing import *

from wikiparse.utils import isiterable
from ..ast import AST, ASTList

class Renderer:
  """Base class for specialized renderers.
  
  WikiParse currently comes with one predefined renderer: the
  `IdentifierRenderer`, which is used to render an arbitrary AST into
  a valid identifier for templates and variables.
  
  In the future, WikiParse will ship a default `HTMLRenderer`.
  
  Implementation of a custom renderer is intended to be facilitated
  by defining specialized `render_{name}(self, ast: AST)` methods
  where `name` is equal to `ast.name`. For more complex behavior, one
  may choose to override the `render` method directly.
  
  `render` should be called after transclusion.
  """
  def __init__(self, name: str):
    self.name = name
  
  def render(self, ast: ASTList) -> str:
    if type(ast) is str:
      return ast
    if isiterable(ast):
      return ''.join(map(self.render, ast))
    if AST.isastlike(ast):
      fn = f'render_{ast.name}'
      if hasattr(self, fn):
        return getattr(self, fn)(ast)
      else:
        return self.fallback_render(ast)
    return str(ast)
  
  def fallback_render(self, node: AST) -> str:
    raise NotImplementedError()
