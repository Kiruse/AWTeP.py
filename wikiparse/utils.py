"""Some utility functions used across the library."""
from __future__ import annotations
from typing import *

NotFound = object()

def first(it: Iterable[T]) -> T:
  return next(iter(it))

def isiterable(it) -> bool:
  try:
    iter(it)
    return True
  except TypeError:
    return False

def iterable(x) -> Iterable:
  return x if isiterable(x) else (x,)

T = TypeVar("T")
