from __future__ import annotations
from typing import *

from ..ast import FormatNode, TextNode
from .renderer import Renderer

class IdentifierRenderer(Renderer):
  def render_text(self, node: TextNode):
    return node.children[0]
  
  def render_bold(self, node: FormatNode):
    return self.render_format(node)
  def render_italic(self, node: FormatNode):
    return self.render_format(node)
  def render_underline(self, node: FormatNode):
    return self.render_format(node)
  def render_format(self, node: FormatNode):
    return self.render(node.children)
