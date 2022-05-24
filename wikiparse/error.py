from typing import *
from .source_reader import SourceReader

class ParserError(Exception):
  def __init__(self, msg: str, reader: SourceReader):
    super().__init__(f'{reader.file}[{reader.line}:{reader.column}]: {msg}')
class RedirectError(Exception):
  def __init__(self, url: str, word: Optional[str] = None):
    super().__init__(RedirectError.make_message(word, url))
    self.word = word
    self.url  = url
  
  @staticmethod
  def make_message(word: Optional[str], url: str):
    if word:
      return f'{word} redirects to {url}'
    else:
      return f'redirects to {url}'
class SkipNode(Exception):
  pass