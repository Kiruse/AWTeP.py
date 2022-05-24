# WikiParse
Another WikiText aka. WikiCode aka. MediaWiki Parser - because I had various issues with others.

*WikiParse* uses a completely different approach and a completely custom parser with few dependencies. It is designed to allow extension of syntax and to create more distinct yet generic abstract syntax trees (ASTs).


# Abstract Syntax Tree
The parser produces an *Abstract Syntax Tree (AST)* which can be further used to render HTML. This AST follows a simple yet special formula:

1. Every AST node has a `name` and `children`, and
2. `children` must only ever exist of `ASTList` - i.e. a recursively nested sequence (list or tuple) of AST nodes + strings or numbers.

When processing the AST, one should always treat `children` like such an `ASTList`. Specifically, this means distinguishing between `str` and other iterable types.

All currently supported AST nodes are listed in `wikiparse.ast`. However, none of these types are instances of the `AST` base - they are merely compatible, treating `AST` more like an interface than a common base class.

The AST node is not designed to implement logic. It is solely designed as a compact data carrier. All parsing logic is implemented in `wikiparse.parser`.
