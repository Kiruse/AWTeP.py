from __future__ import annotations
from typing import *
from .interface.logger import Logger

class StateError(Exception): pass

class SourceReader:
  def __init__(self, source: str, file: str = '', logger: Logger | None = None):
    self.source = source
    self.offset = 0
    self.file = file
    self.line = 1
    self.column = 0
    self.is_line_start = True # ignores whitespaces at the beginning of the line
    self.log = logger
  
  def __len__(self):
    return len(self.source) - self.offset
  
  def next(self, n = 1) -> str:
    if len(self) < n:
      raise EOFError()
    
    if n > 1:
      return ''.join(map(lambda i: self.next(), range(n)))
    
    c = self.source[self.offset]
    
    self.offset += 1
    if c == '\n':
      self.line += 1
      self.column = 0
      self.is_line_start = True
    else:
      self.column += 1
    
    self.is_line_start = self.is_line_start and c.isspace()
    
    return c
  
  def peek(self, n: int = 1, *, no_eof = True) -> str:
    if n > len(self) and no_eof:
      raise EOFError()
    return self.source[self.offset:self.offset+n]
  
  def peeks(self, s: str, *, no_eof = True, case_sensitive = True) -> bool:
    peeked = self.peek(len(s), no_eof=no_eof)
    if not case_sensitive:
      return peeked.lower() == s.lower()
    return self.peek(len(s), no_eof=no_eof) == s
  
  def skip(self, n: int = 1):
    for _ in range(n):
      self.next()
  
  def consume(self, s: str, case_sensitive = True, *, no_eof = False):
    """Consume `s` iff source at current offset matches `s`, optionally matching case."""
    l = len(s)
    ref = self.peek(l, no_eof=no_eof)
    if (not case_sensitive and ref.lower() == s.lower()) or (case_sensitive and ref == s):
      try:
        self.skip(l)
        return True
      except:
        if not no_eof:
          raise
        return False
    return False
  
  def consume_until(self,
    delim: str | Sequence[str] | Callable[[SourceReader], bool],
    case_sensitive = True,
    *,
    no_eof = False
  ):
    """Consume characters until any character or sequence from `any`
    is found, optionally matching case."""
    def isterminated():
      try:
        return delim(self)
      except TypeError:
        return any(map(lambda d: self.peeks(d, case_sensitive=case_sensitive, no_eof=True), delim))
    
    consumed = ''
    
    while len(self) and not isterminated():
      consumed += self.next()
    
    if not isterminated() and not no_eof:
      raise EOFError()
    return consumed
  
  def __getitem__(self, idx: Union[int, slice]) -> str:
    try:
      return self.source[self.offset + idx]
    except TypeError:
      newStart = idx.start + self.offset if idx.start else self.offset
      newStop  = idx.stop  + self.offset if idx.stop  else None
      
      newSlice = slice(newStart, newStop, idx.step)
      return self.source[newSlice]
  
  def copy(self) -> SourceReader:
    copied = SourceReader(self.source, self.file)
    copied.offset = self.offset
    copied.line = self.line
    copied.column = self.column
    copied.is_line_start = self.is_line_start
    return copied
  
  def copyfrom(self, other: SourceReader):
    self.source = other.source
    self.offset = other.offset
    self.line = other.line
    self.column = other.column
    self.is_line_start = other.is_line_start
    self.file = other.file
    return self
  
  def consumer(self):
    """Create a `SourceConsumer` at the current source location."""
    return SourceConsumer(self)
  
  def __str__(self):
    return self.source[self.offset:]
  
  def __repr__(self):
    return f'[{self.file}:{self.line}:{self.column}] {self.source[self.offset:]}'

class SourceConsumer(SourceReader):
  """A `SourceConsumer` is a `with` resource which advances the underlying `SourceReader` only when the `with` block
  does not raise an exception."""
  def __init__(self, source: SourceReader):
    self._source = source
    self.log = source.log
  
  def revert(self):
    self.copyfrom(self._source)
    return self
  
  def __enter__(self):
    self.copyfrom(self._source)
    self._entry_offset = self.offset
    return self
  
  def __exit__(self, exc_type, exc_val, exc_tb):
    if not exc_type:
      if self._entry_offset != self._source.offset:
        raise StateError('SourceReader advanced independently from SourceConsumer')
      self._source.skip(len(self._source) - len(self))
