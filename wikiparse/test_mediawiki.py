from typing import *
from iso639 import Lang
from .mediawiki import MediaWiki, WikiNamespace
import pytest

def test_construct():
  mw = MediaWiki()
  assert mw.host == 'wikipedia.org'
  assert mw.language == Lang('en')
  
  mw = MediaWiki('wiktionary.org')
  assert mw.host == 'wiktionary.org'
  assert mw.language == Lang('en')
  
  mw = MediaWiki('wiktionary.org', language='de')
  assert mw.host == 'wiktionary.org'
  assert mw.language == Lang('de')

@pytest.mark.asyncio
async def test_query_namespaces():
  mw = MediaWiki(language='de')
  assert await mw.query_namespaces()
  
  ns = mw.namespaces[6]
  assert type(ns) is WikiNamespace
  assert ns.id == 6
  assert ns.name == 'Datei'
  assert ns.canonical == 'File'
  assert 'Image' in ns.aliases and 'Bild' in ns.aliases

@pytest.mark.asyncio
async def test_get_revision():
  mw = MediaWiki()
  assert await mw.get_revision('Main Page')
  
  mw = MediaWiki('wikipedia.org', language='de')
  assert await mw.get_revision('Hauptseite')
  
  mw = MediaWiki('wikipedia.org', language='fr')
  assert await mw.get_revision('Main Page')

@pytest.mark.asyncio
async def test_get_revisions_for():
  mw = MediaWiki('wiktionary.org', language='de')
  revs = await mw.get_revisions_for(('Main Page', 'Template:K'))
  assert revs
  assert 'Main Page' in revs
  assert 'Vorlage:K' in revs # canonical title in German

@pytest.mark.asyncio
async def test_fetch_page():
  mw = MediaWiki('wiktionary.org', language='de')
  assert await mw.fetch_page('Hund')
  assert await mw.fetch_template('K')

@pytest.mark.asyncio
async def test_page_properties():
  mw = MediaWiki('wiktionary.org', language='de')
  await mw.query_namespaces()
  
  page = await mw.fetch_template('K')
  assert page.title == 'Vorlage:K'
  assert page.pagename == 'K'
  assert page.fullpagename == 'Vorlage:K'
