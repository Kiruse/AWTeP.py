from __future__ import annotations
import re
from typing import *

from ..ast import *
from .identifier import IdentifierRenderer
from .renderer import Renderer

identifier_renderer = IdentifierRenderer()

# these nodes aren't actually rendered - they convey information on
# their contents and how to render them without being rendered themselves.
META_NODES = ('noinclude', 'includeonly', 'onlyinclude', 'nowiki')

class HTMLRenderer(Renderer):
  def __init__(self):
    super().__init__()
  
  def render_text(self, text: TextNode):
    return text.children[0]
  
  def render_italic(self, node: FormatNode):
    return self.render_simple_tag('i', node.children)
  
  def render_bold(self, node: FormatNode):
    return self.render_simple_tag('b', node.children)
  
  def render_underline(self, node: FormatNode):
    return self.render_simple_tag('u', node.children)
  
  def render_simple_tag(self, tag: str, contents: ASTList):
    return f'<{tag}>{self.render(contents)}</{tag}>'
  
  def render_html(self, node: HTMLNode):
    tag, attributes, content = node.children
    if len(attributes):
      sattrs = ' '.join(map(lambda attr: f'{renderid(attr.children[0])}="{htmlescape(self.render(attr.children[1]))}"', attributes))
      return f'<{tag} {sattrs}>{self.render(content)}</{tag}>'
    else:
      return f'<{tag}>{self.render(content)}</{tag}>'
  
  def fallback_render(self, node: AST) -> str:
    if node.name in META_NODES:
      return self.render(node.children)
    raise NotImplementedError()

def htmlescape(s: str) -> str:
  s = re.sub('"', '\\"', s)
  s = re.sub("'", "\\'", s)
  s = re.sub(r'\\', r'\\', s)
  return s

def renderid(ast: ASTList) -> str:
  return identifier_renderer.render(ast)
