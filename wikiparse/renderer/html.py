from __future__ import annotations
import re
from typing import *

from ..ast import *
from .identifier import IdentifierRenderer
from .renderer import Renderer

identifier_renderer = IdentifierRenderer()

class HTMLRenderer(Renderer):
  """The standard `HTMLRenderer` which can render most standard AST nodes (from the `wikiparse.ast` module).
  Transclusion-specific nodes (templates, variables, parser functions, and magic words) are not rendered as they should
  be transcluded before rendering anyways. The `DefRefNode`, which is a non-standard node in the WikiText specification
  to be refactored in a future update, is also not handled by this renderer.
  
  **Note:** The `IndentNode` is currently rendered using MediaWiki standard *<dd>* tag. Subjectively, this is a
  non-semantic use of the tag and should be overridden.
  
  **Caveat:** Multi-level lists are somewhat non-trivial to handle properly and depend partially on your specific
  rendering needs. Normally, multi-level lists would be rendered by wrapping another *<ol>* or *<ul>* HTML tag in an
  *<li>* tag, but this does not exactly align with the WikiText notation. A better representation would be to add left
  visual padding to the list items. So instead of enforcing a standard solution here, this renderer produces *<li>* tags
  following this pattern: `<li data-depth="{depth}">{content}</li>`. If indeed a nested representation is desired, it is
  recommended to apply a custom `Transformer` which groups consecutive list items of the same depth into their own list
  node, and perhaps override the `render_list` method.
  """
  def __init__(self):
    super().__init__()
  
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
  
  def render_heading(self, h: HeadingNode):
    cnt, lvl = h.children
    return f'<h{lvl}>{self.render(cnt)}</h{lvl}>'
  
  def render_link(self, link: LinkNode):
    label, url = link.children
    return f'<a href="{htmlescape(self.render(url))}">{self.render(label)}</a>'
  
  def render_linebreak(self, _):
    return '<br/>'
  
  def render_list(self, list: ListNode):
    ordered, items = list.children
    tag = 'ol' if ordered else 'ul'
    return f'<{tag}>{self.render(items)}</{tag}>'
  
  def render_listitem(self, item: ListItemNode):
    depth, cnt = list.children
    return f'<li data-depth="{depth}">{self.render(cnt)}</li>'

def htmlescape(s: str) -> str:
  s = re.sub('"', '\\"', s)
  s = re.sub("'", "\\'", s)
  s = re.sub(r'\\', r'\\', s)
  return s

def renderid(ast: ASTList) -> str:
  return identifier_renderer.render(ast)
