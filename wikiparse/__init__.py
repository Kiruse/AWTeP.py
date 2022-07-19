from .ast import AST, ASTList
from .mediawiki import MediaWiki
from .parser import parse, parsepage
from .renderer import HTMLRenderer
from .transformer.transformer import make_vars, Variables
parsetpl = parsepage
