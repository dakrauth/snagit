import bs4

BAD_ATTRS = 'align alink background bgcolor border clear height hspace language link nowrap start text type valign vlink vspace width'.split()
NON_CLOSING = 'hr br link meta img base input param source'.split()
NO_INDENT = 'body head tbody thead tfoot'.split()


#-------------------------------------------------------------------------------
def get_attrs(el):
    attrs = {}
    orig = getattr(el, 'attrs', {}) or {}
    for key, values in orig.items():
        attrs[key] = ' '.join(values) if isinstance(values, (list, tuple)) else values
    return attrs


#-------------------------------------------------------------------------------
def format_element(el, lines, depth=0, prefix='    '):
    indent = prefix * depth
    if isinstance(el, bs4.NavigableString):
        el = el.strip()
        if el:
            lines.append(u'{}{}'.format(indent, el))
        return lines
        
    tag = el.name
    s = u'{}<{}'.format(indent, tag)
    
    attrs = get_attrs(el)
    for k, v in attrs.items():
        s += u' {}="{}"'.format(k, v)
    
    s += u'>'
    if tag in NON_CLOSING:
        lines.append(s)
        return lines

    children = el.contents
    n_children = len(children)
    if children:
        if n_children > 1 or isinstance(children[0], bs4.Tag):
            lines.append(s)
            for child in children:
                lines = format_element(
                    child,
                    lines,
                    depth if child.name in NO_INDENT else depth + 1,
                    prefix
                )
            lines.append(u'{}</{}>'.format(indent, tag))
            return lines
        else:
            lines.append(u'{}{}</{}>'.format(s, children[0].strip(), tag))
    else:
        lines.append(u'{}</{}>'.format(s, tag))
    
    return lines

#-------------------------------------------------------------------------------
def format(el, depth=0, prefix='    ', doctype=True):
    lines = []
    start = 0
    if isinstance(el, bs4.BeautifulSoup) and el.contents:
        first = el.contents[0]
        if isinstance(first, bs4.Doctype):
            lines.append(unicode(first.output_ready()))
            start = 1

    for child in el.contents[start:]:
        lines = format_element(child, lines, depth, prefix)

    # from pprint import pprint; pprint(lines)
    return u'\n'.join(lines)


bs4format = format
