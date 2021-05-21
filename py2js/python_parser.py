"""
Grammar-complete Python Parser
==============================

A fully-working Python 2 & 3 parser (but not production ready yet!)

This example demonstrates usage of the included Python grammars
"""
from lark import Lark, Tree
from lark.indenter import Indenter

# __path__ = os.path.dirname(__file__)

_comments = []  # XXX not thread-safe

class PythonIndenter(Indenter):
    NL_type = '_NEWLINE'
    OPEN_PAREN_types = ['LPAR', 'LSQB', 'LBRACE']
    CLOSE_PAREN_types = ['RPAR', 'RSQB', 'RBRACE']
    INDENT_type = '_INDENT'
    DEDENT_type = '_DEDENT'
    tab_len = 8


def add_comment(n):
    if '#' in n:
        _comments.append(n)
    return n

callbacks = {'COMMENT': add_comment, '_NEWLINE': add_comment}

python_parser3 = Lark.open('python3.lark',parser='lalr',
    rel_to=__file__,
    postlex=PythonIndenter(),
    start='file_input',
    cache=True,
    propagate_positions=True,
    lexer_callbacks=callbacks,
    maybe_placeholders=True
)


def parse(text):
    assert not _comments
    tree = python_parser3.parse(text)
    # AssignComments().assign_comments(tree, _comments)
    assign_comments(tree, _comments)

    return tree

def assign_comments(tree, comments):
    nodes_by_line = classify(tree.iter_subtrees(), lambda t: getattr(t.meta, 'line', None))
    nodes_by_line.pop(None,None)
    rightmost_nodes = {line: max(nodes, key=lambda n: n.meta.column) for line, nodes in nodes_by_line.items()}
    leftmost_nodes  = {line: min(nodes, key=lambda n: n.meta.column) for line, nodes in nodes_by_line.items()}

    for c in comments:
        if c.line == c.end_line:
            n = rightmost_nodes[c.end_line]
            assert not hasattr(n.meta, 'inline_comment')
            n.meta.inline_comment = c
        else:
            if c.end_line not in leftmost_nodes:
                # Probably past the end of the file
                # XXX verify this is the case
                continue

            n = leftmost_nodes[c.end_line]
            header_comments = getattr(n.meta, 'header_comments', [])
            n.meta.header_comments = header_comments + [c]



def classify(seq, key=None, value=None):
    d = {}
    for item in seq:
        k = key(item) if (key is not None) else item
        v = value(item) if (value is not None) else item
        if k in d:
            d[k].append(v)
        else:
            d[k] = [v]
    return d