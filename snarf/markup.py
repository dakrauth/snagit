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
    def format_element(self, el, lines, depth=0, prefix='    '):
        indent = prefix * depth
        if isinstance(el, bs4.NavigableString):
            el = el.strip()
            if el:
                lines.append('{}{}'.format(indent, el))
            return lines
        
    
        line = '{}<{}'.format(indent, el.name)
        for k, v in self.get_attrs(el).items():
            line += ' {}="{}"'.format(k, v)
    
        line += '>'
        if el.name in self.non_closing:
            lines.append(line)
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
        start = 0
        if isinstance(el, bs4.BeautifulSoup) and el.contents:
            first = el.contents[0]
            if isinstance(first, bs4.Doctype):
                lines.append(str(first.output_ready()).strip())
                start = 1

        for child in el.contents[start:]:
            lines = self.format_element(child, lines, depth, prefix)

        # from pprint import pprint; pprint(lines)
        return '\n'.join(lines)


_formatter = None

#-------------------------------------------------------------------------------
def format(*args, **kws):
    global _formatter
    if not _formatter:
        _formatter = Formatter()
        
    _formatter.format(*args, **kws)
