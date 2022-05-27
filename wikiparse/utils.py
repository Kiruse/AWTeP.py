"""Some utility functions used across the library."""
from __future__ import annotations
from typing import *

def first(it: Iterable[T]) -> T:
  return next(iter(it))

T = TypeVar("T")
