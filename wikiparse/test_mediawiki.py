from typing import *
from iso639 import Lang
from .mediawiki import MediaWiki
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
