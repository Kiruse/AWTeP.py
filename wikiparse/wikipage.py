from __future__ import annotations
from typing import *
from .ast import ASTList
from .interface import Logger
from .parser import parsepage

class WikiNamespace:
  "Simple data class storing meta data on a WikiMedia project namespace."
  def __init__(self, name: str, canonical: str | None, aliases: Sequence[str], id: int):
    self.name = name
    self.canonical = canonical
    self.aliases = aliases
    self.id = id

class WikiPage:
  "Simple data class storing contents & meta data about a specific WikiMedia page."
  def __init__(self, title: str, content: str, format: str, namespace: WikiNamespace):
    self.title = title
    self.content = content
    self.format = format
    self.namespace = namespace
    self._ast: Tuple[ASTList, ASTList] | None = None
  
  def parse(self, *, logger: Logger | None = None):
    """Parse the WikiText of the represented page and cache it.
    Returns a tuple of directives & AST."""
    if self._ast is None:
      self._ast = parsepage(self.content, self.title, logger=logger)
    return self._ast
  
  @property
  def pagename(self):
    return self.title[len(self.namespace.name)+1:]
  
  @property
  def fullpagename(self):
    return self.title
