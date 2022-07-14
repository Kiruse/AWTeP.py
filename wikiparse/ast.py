"""AST Node Types for more concrete typing in AST nodes."""
from __future__ import annotations
from typing import *
from .utils import isiterable

class AST:
  def __init__(self, name: str, children: List = []):
    self.name = name
    self.children = children
  
  def __repr__(self):
    return f'{self.name}({", ".join(map(repr, self.children))})'
  
  def __eq__(self, other: AST) -> bool:
    if not hasattr(other, 'name') or not hasattr(other, 'children'):
      return False
    if self.name != other.name:
      return False
    if len(self.children) != len(other.children):
      return False
    for i in range(0, len(self.children)):
      if self.children[i] != other.children[i]:
        return False
    return True
  
  @staticmethod
  def clone(ast: ASTList) -> ASTList:
    """Clone the given AST recursively. If it is a single node, the clone will also be a single node. If it is a list of
    nodes, the clone will be an array of clones. Only nested arrays of primitives and AST nodes are supported. If a node
    contains a dictionary, for example, it will be copied by reference.
    """
    if isiterable(ast) and not type(ast) is str:
      copy: List[AST] = []
      for node in ast:
        copy.append(AST.clone(node))
      return copy
    if AST.isastlike(ast):
      return AST(ast.name, AST.clone(ast.children))
    return ast
  
  @staticmethod
  def isastlike(x) -> bool:
    return isinstance(x, object) and hasattr(x, 'name') and hasattr(x, 'children')

class TextNode(AST):
  def __init__(self, text: str):
    self.name = 'text'
    self.children = (text,)
  
  @staticmethod
  def lstrip(node: TextNode):
    txt = node.children[0].lstrip()
    return TextNode(txt) if txt else None
  
  @staticmethod
  def rstrip(node: TextNode):
    txt = node.children[0].rstrip()
    return TextNode(txt) if txt else None

class NewlineNode(AST):
  def __init__(self):
    self.name = 'newline'
    self.children = ()

class HeadingNode(AST):
  def __init__(self, title: ASTList, level: int):
    self.name = 'heading'
    self.children = (title, level)

class TemplateNode(AST):
  def __init__(self, name: TemplateName, posargs: Sequence[PosArgNode], namedargs: Sequence[NamedArgNode]):
    self.name = 'template'
    self.children = (name, posargs, namedargs)

class InvokeNode(AST):
  """Variant of `TemplateNode` representing "Module:" namespace templates.
  These templates are not actually WikiText, but LUA scripts to be executed instead.
  However, we currently do not support LUA scripting."""
  def __init__(self, module: ASTList, function: ASTList, posargs: Sequence[PosArgNode], namedargs: Sequence[NamedArgNode]):
    self.name = 'invoke'
    self.children = (module, function, posargs, namedargs)

class PosArgNode(AST):
  def __init__(self, values: ASTList):
    self.name = 'posarg'
    self.children = (values,)

class NamedArgNode(AST):
  def __init__(self, name: ASTList, values: ASTList):
    self.name = 'namedarg'
    self.children = (name, values)

class VariableNode(AST):
  def __init__(self, name: TemplateName, defaults: Optional[ASTList]):
    self.name = 'variable'
    self.children = (name, defaults)

class IfNode(AST):
  def __init__(self, condition: ASTList, true: ASTList, false: ASTList):
    self.name = 'if'
    self.children = (condition, true, false)

class IfEqNode(AST):
  def __init__(self, lhs: ASTList, rhs: ASTList, true: ASTList, false: ASTList):
    self.name = 'ifeq'
    self.children = (lhs, rhs, true, false)

class IfExistNode(AST):
  def __init__(self, file: ASTList, true: ASTList, false: ASTList):
    self.name = 'ifexist'
    self.children = (file, true, false)

class SwitchNode(AST):
  def __init__(self, value: ASTList, branches: Sequence[SwitchBranchNode]):
    self.name = 'switch'
    self.children = (value, branches)

class SwitchBranchNode(AST):
  def __init__(self, ref: ASTList, rep: ASTList):
    self.name = 'linkbranch'
    self.children = (ref, rep)

class LinkNode(AST):
  def __init__(self, label: ASTList, url: ASTList):
    self.name = 'link'
    self.children = (label, url)

class NoWikiNode(AST):
  def __init__(self, content: str = ''):
    self.name = 'nowiki'
    self.children = (content,)

class NoIncludeNode(AST):
  def __init__(self, contents: ASTList):
    self.name = 'noinclude'
    self.children = contents

class OnlyIncludeNode(AST):
  def __init__(self, contents: ASTList):
    self.name = 'onlyinclude'
    self.children = contents

class IncludeOnlyNode(AST):
  def __init__(self, contents: ASTList):
    self.name = 'includeonly'
    self.children = contents

class CommentNode(AST):
  def __init__(self, content: str):
    self.name = 'comment'
    self.children = (content,)

class FormatNode(AST):
  def __init__(self, type: Literal['bold', 'italic', 'underline'], values: ASTList):
    self.name = type
    self.children = values

class IndentNode(AST):
  def __init__(self, count: int):
    self.name = 'indent'
    self.children = (count,)

class LineBreakNode(AST):
  def __init__(self):
    self.name = 'linebreak'
    self.children = ()

class DefRefNode(AST):
  def __init__(self, defids: Sequence[str]):
    self.name = 'defref'
    self.children = (defids,)

class ListNode(AST):
  def __init__(self, ordered: bool, items: List[ListItemNode]):
    self.name = 'list'
    self.children = (ordered, items)

class ListItemNode(AST):
  def __init__(self, depth: int, content: ASTList):
    self.name = 'listitem'
    self.children = (depth, content)

class HTMLNode(AST):
  def __init__(self, tag: str, attributes: Sequence[HTMLAttributeNode], contents: ASTList):
    self.name = 'html'
    self.children = (tag, attributes, contents)

class HTMLAttributeNode(AST):
  def __init__(self, name: ASTList, value: ASTList | None):
    self.name = 'html-attrib'
    self.children = (name, value)

TemplateName = Sequence[Union[TextNode, VariableNode]]
ConditionalNode = Union[IfNode, IfEqNode, IfExistNode, SwitchNode]
BracesNode = Union[TemplateNode, InvokeNode, VariableNode, ConditionalNode]
ASTList = Union[AST, List["ASTList"]]
