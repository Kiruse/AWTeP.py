"""Central configuration for a specific MediaWiki project."""
from __future__ import annotations
import asyncio
from typing import *
from iso639 import Lang
from piodispatch import ascoroutine

from .ast import AST
from .error import APIError
from .interface.requester import Requester
from .interface.logger import Logger
from .parser import parsepage
from .utils import first
import requests

rget = ascoroutine(requests.get)

class MediaWiki:
  def __init__(self, host = 'wikipedia.org', **kwargs):
    self.host = host
    self.language: Lang = Lang(kwargs.pop('language', 'en')) # raises if language is invalid
    self.requester: Requester | None = kwargs.pop('requester', None)
    self.logger: Logger | None = kwargs.pop('logger', None)
  
  @property
  def baseurl(self) -> str:
    return f'https://{self.language.pt1}.{self.host}'
  
  async def fetch_page(self, title: str, *, namespace: str = '') -> List[AST]:
    "Fetch the given page's parsed WikiText as an AST."
    file = f'{namespace}:{title}' if namespace else title
    src = await self.get_revision(file)
    return parsepage(src, file, logger=self.logger)
  
  async def fetch_template(self, name: str) -> List[AST]:
    return await self.fetch_page(name, namespace='Template')
  
  async def fetch_module(self, name: str) -> str:
    "Fetching a Module differs from fetching a regular page in that it returns the raw LUA source code as a string."
    raise NotImplementedError()
  
  async def get_revision(self, title: str, *args, **kwargs) -> str:
    """Shortcut for `MediaWiki.get_revisions_for((title,), *args, **kwargs)`.
    Thus accepts the same positional and keyword arguments as `MediaWiki.get_revisions_for`."""
    return await self.get_revisions_for((title,), *args, **kwargs)
  
  async def get_revisions_for(self, titles: Sequence[str]) -> Dict[str, Revision] | Revision:
    """Retrieve the latest revision for each page listed by `titles`.
    Return a single revision if only one title is given, otherwise a mapping from title to revision.
    """
    get = self.requester.get if self.requester else rget
    
    params = {
      'action': 'query',
      'titles': '|'.join(titles),
      'prop': 'revisions',
      'rvprop': 'content',
      'rvslots': 'main',
      'format': 'json',
    }
    
    res = await get(f'{self.baseurl}/w/api.php', params=params)
    json = res.json()
    
    if 'error' in json:
      raise APIError(json['error']['info'])
    
    pages = json['query']['pages'].values()
    if len(titles) == 1:
      return await self._get_revision_from(first(pages))
    else:
      # map pages/titles to list of revisions
      return dict(
        zip(
          (page['title'] for page in pages),
          await asyncio.gather(*(
            self._get_revision_from(page)
            for page in pages
          ))
        )
      )
  
  async def _get_revision_from(self, data: Dict) -> List[str]:
    if 'revisions' not in data:
      raise FileNotFoundError(f'page "{self.baseurl}/wiki/{data["title"]}" not found')
    
    rev = data['revisions'][0]['slots']['main']
    assert rev['contentmodel'] == 'wikitext'
    assert rev['contentformat'] == 'text/x-wiki'
    return rev['*']

Revision = Union[str, List[str]]
