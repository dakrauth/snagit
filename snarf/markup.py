from __future__ import unicode_literals
import bs4
from .compat import str
from . import utils

#===============================================================================
class Formatter(object):

    #---------------------------------------------------------------------------
    def __init__(self):
        self.non_closing = utils.get_config('non_closing_tags')
        self.no_indent = utils.get_config('no_indent_tags')
        
    #---------------------------------------------------------------------------
    def get_attrs(self, el):
        orig = getattr(el, 'attrs', {}) or {}
        return {
            key: ' '.join(values) if isinstance(values, (list, tuple)) else values
            for key, values in orig.items()
        }

    #---------------------------------------------------------------------------
    def format_attrs(self, el):
        attrs = ''
        orig = getattr(el, 'attrs', {}) or {}
        if orig:
            for key, vals in orig.items():
                vals = ' '.join(vals) if isinstance(vals, (list, tuple)) else vals
                attrs += ' {}="{}"'.format(key, vals)
            
        return attrs

    #---------------------------------------------------------------------------
    def format_element(self, el, lines, depth=0, prefix='    '):
        indent = prefix * depth
        if isinstance(el, bs4.NavigableString):
            el = el.strip()
            if el:
                lines.append('{}{}'.format(indent, el))
            return lines
        
        line = '{}<{}{}>'.format(indent, el.name, self.format_attrs(el))
        if el.name in self.non_closing:
            lines.append(line)
            for ct in el.contents:
                lines = self.format_element(ct, lines, depth, prefix)
            return lines
        
        n_children = len(el.contents)
        if n_children:
            if n_children > 1 or isinstance(el.contents[0], bs4.Tag):
                lines.append(line)
                for ct in el.contents:
                    ct_depth = depth if ct.name in self.no_indent else depth + 1
                    lines = self.format_element(ct, lines, ct_depth, prefix)
                lines.append('{}</{}>'.format(indent, el.name))
            else:
                lines.append('{}{}</{}>'.format(line, el.contents[0].strip(), el.name))
        else:
            lines.append('{}</{}>'.format(line, el.name))
    
        return lines

    #---------------------------------------------------------------------------
    def format(self, el, depth=0, prefix='    ', doctype=True):
        lines = []
        if not el and el.contents:
            return ''
        
        contents = iter(el.contents)
        if isinstance(el, bs4.BeautifulSoup):
            first = el.contents[0]
            if isinstance(first, bs4.Doctype):
                lines.append(str(first.output_ready()).strip())
                next(contents)

        for child in contents:
            lines = self.format_element(child, lines, depth, prefix)

        # from pprint import pprint; pprint(lines)
        return '\n'.join(lines)


_formatter = None

#-------------------------------------------------------------------------------
def format(*args, **kws):
    global _formatter
    if not _formatter:
        _formatter = Formatter()
        
    return _formatter.format(*args, **kws)
