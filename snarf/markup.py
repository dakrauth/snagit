from __future__ import unicode_literals
import bs4
from six import u as text

BAD_ATTRS = 'align alink background bgcolor border clear height hspace language link nowrap start text type valign vlink vspace width'.split()
NON_CLOSING = 'hr br link meta img base input param source'.split()
NO_INDENT = 'body head tr'.split()


#-------------------------------------------------------------------------------
def get_attrs(el):
    orig = getattr(el, 'attrs', {}) or {}
    return {
        key: ' '.join(values) if isinstance(values, (list, tuple)) else values
        for key, values in orig.items()
    }


#-------------------------------------------------------------------------------
def format_element(el, lines, depth=0, prefix='    '):
    indent = prefix * depth
    if isinstance(el, bs4.NavigableString):
        el = el.strip()
        if el:
            lines.append('{}{}'.format(indent, el))
        return lines
        
    
    line = '{}<{}'.format(indent, el.name)
    for k, v in get_attrs(el).items():
        line += ' {}="{}"'.format(k, v)
    
    line += '>'
    if el.name in NON_CLOSING:
        lines.append(line)
        return lines

    n_children = len(el.contents)
    if n_children:
        if n_children > 1 or isinstance(el.contents[0], bs4.Tag):
            lines.append(line)
            for ct in el.contents:
                ct_depth = depth if ct.name in NO_INDENT else depth + 1
                lines = format_element(ct, lines, ct_depth, prefix)
            lines.append('{}</{}>'.format(indent, el.name))
        else:
            lines.append('{}{}</{}>'.format(line, el.contents[0].strip(), el.name))
    else:
        lines.append('{}</{}>'.format(line, el.name))
    
    return lines

#-------------------------------------------------------------------------------
def format(el, depth=0, prefix='    ', doctype=True):
    lines = []
    start = 0
    if isinstance(el, bs4.BeautifulSoup) and el.contents:
        first = el.contents[0]
        if isinstance(first, bs4.Doctype):
            lines.append(text(first.output_ready()).strip())
            start = 1

    for child in el.contents[start:]:
        lines = format_element(child, lines, depth, prefix)

    # from pprint import pprint; pprint(lines)
    return '\n'.join(lines)
