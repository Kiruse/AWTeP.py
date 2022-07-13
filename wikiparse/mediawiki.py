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
  """`MediaWiki` is your interface to an arbitrary WikiMedia style wiki website.
  
  The constructor supports different, optional keyword arguments:
  * `language: str` to use, using ISO-639 language codes. Defaults to `'en'`.
  * `requester: Requester` web request limiter. Optional.
  * `logger: Logger` instance to use. Currently not used internally, but can be useful to carry through. Optional.
  * `namespaces: Dict[str | int, WikiNamespace]` mapping of namespace IDs and/ornames to `WikiNamespace` instances.
    Optional. Should be populated at runtime using `await wiki.query_namespaces()`.
  """
  def __init__(self, host = 'wikipedia.org', **kwargs):
    self.host = host
    self.language: Lang = Lang(kwargs.pop('language', 'en')) # raises if language is invalid
    self.requester: Requester | None = kwargs.pop('requester', None)
    self.logger: Logger | None = kwargs.pop('logger', None)
    self.namespaces: Dict[str | int, WikiNamespace] = {}
  
  @property
  def baseurl(self) -> str:
    return f'https://{self.language.pt1}.{self.host}'
  
  async def query_namespaces(self):
    """Query the namespaces of this MediaWiki project."""
    get = self.requester.get if self.requester else rget
    
    params = {
      'action': 'query',
      'meta': 'siteinfo',
      'siprop': 'namespaces|namespacealiases',
      'format': 'json',
    }
    
    res = await get(f'{self.baseurl}/w/api.php', params=params)
    json = res.json()
    
    if 'error' in json:
      raise APIError(json['error']['info'])
    assert 'batchcomplete' in json
    
    for ns in json['query']['namespaces'].values():
      inst = WikiNamespace(ns['*'], ns['canonical'] if 'canonical' in ns else None, [], ns['id'])
      self.namespaces[inst.id] = inst
      self.namespaces[inst.name] = inst
      if inst.canonical:
        self.namespaces[inst.canonical] = inst
    for alias in json['query']['namespacealiases']:
      inst = self.namespaces[alias['id']]
      inst.aliases.append(alias['*'])
      self.namespaces[alias['*']] = inst
    
    return self
  
  async def fetch_page(self, title: str, *, namespace: str = '') -> WikiPage:
    "Fetch the given page's parsed WikiText as an AST."
    file = f'{namespace}:{title}' if namespace else title
    page = await self.get_revision(file)
    page.parse()
    return page
  
  async def fetch_template(self, name: str) -> WikiPage:
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
    return WikiPage(
      data['title'],
      rev['*'],
      rev['contentformat'],
      self.namespaces[data['ns']] if data['ns'] in self.namespaces else DEFAULT_NS
    )

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
    self._ast: Tuple[List[AST], List[AST]] | None = None
  
  def parse(self, *, logger: Logger | None = None) -> List[AST]:
    if self._ast is None:
      self._ast = parsepage(self.content, self.title, logger=logger)
    return self._ast
  
  @property
  def pagename(self):
    return self.title[len(self.namespace.name)+1:]
  
  @property
  def fullpagename(self):
    return self.title

Revision = Union[str, List[str]]

DEFAULT_NS = WikiNamespace('', None, [], 0)
