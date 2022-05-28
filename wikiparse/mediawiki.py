"""Central configuration for a specific MediaWiki project."""
from __future__ import annotations
import asyncio
from typing import *
from iso639 import Lang
from piodispatch import ascoroutine

from .ast import AST
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
    return f'https://{self.language.pt1}.{self.host}/'
  
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
  
  async def get_revisions_for(self, titles: Sequence[str], limit = 1) -> Dict[str, Revision] | Revision:
    """Retrieve `limit` revisions for each listed page by `titles`.
    Returns a map of pages to revisions if `len(titles) > 1`.
    Revisions will be either a list of strings or a single string if `limit == 1`.
    """
    get = self.requester.get if self.requester else rget
    
    params = {
      'action': 'query',
      'titles': '|'.join(titles),
      'prop': 'revisions',
      'rvlimit': limit,
      'rvprop': 'content',
      'format': 'json',
    }
    
    res = await get(f'{self.baseurl}/w/api.php', params=params)
    json = res.json()
    
    pages = json['query']['pages'].values()
    if len(titles) == 1:
      revs = await self._get_revisions_from(first(titles), first(pages))
      return first(revs) if limit == 1 else revs
    else:
      # map pages/titles to list of revisions
      return dict(
        zip(
          titles,
          await asyncio.gather((
            self._get_revisions_from(title, page)
            for title, page in zip(titles, pages)
          ))
        )
      )
  
  async def _get_revisions_from(self, title: str, page: Dict) -> List[str]:
    if 'revisions' not in page:
      raise FileNotFoundError(f'page "{title}" not found', page)
    
    revs = []
    for rev in page['revisions']:
      # assert because we've requested wikitext specifically
      assert rev['contentmodel'] == 'wikitext'
      assert rev['contentformat'] == 'text/x-wiki'
      revs.append(rev['*'])
    return revs

Revision = Union[str, List[str]]
