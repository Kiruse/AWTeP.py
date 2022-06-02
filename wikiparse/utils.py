"""Some utility functions used across the library."""
from __future__ import annotations
from typing import *
from .ast import AST, ASTList

def first(it: Iterable[T]) -> T:
  return next(iter(it))

def isiterable(it) -> bool:
  try:
    iter(it)
    return True
  except TypeError:
    return False

def find_nodes(pred: Callable[[AST], bool], ast: ASTList) -> List[AST]:
  if type(ast) is not str and ast is not None:
    for node in ast:
      if type(node) == str:
        continue
      if isiterable(node):
        yield from find_nodes(pred, node)
      elif pred(node):
        yield node

T = TypeVar("T")
