# -*- coding:utf8 -*-
import re
import os
import copy
import json
from pprint import pformat
from collections import deque

try:
    import bs4
except ImportError:
    bs4 = None

from . import utils
from . import markup

is_string = utils.is_string
verbose = utils.verbose

attr_pattern = r'''((?:\s+)([\w:-]+)=('[^']*'|"[^"]*"|[\w.:;&#-]+))'''
attr_re = re.compile(attr_pattern)
start_tag_re = re.compile(r'''<([\w:-]+)(%s+)>''' % (attr_pattern,))

#-------------------------------------------------------------------------------
def normalize_attrs(text):
    def replacement(m):
        tag = m.group(1)
        attrs = []
        for m2 in attr_re.finditer(m.group(2)):
            value = m2.group(3)
            if value.startswith(("'", '"')):
                value = value[1:-1]
            attrs.append(u' {}="{}"'.format(m2.group(2), value))
        return u'<{}{}>'.format(tag, ''.join(attrs))
    return start_tag_re.sub(replacement, text)


#-------------------------------------------------------------------------------
def replace(text, old, new, strip=False):
    '''
    Replace a subset of ``text``.
    
    ``old`` type may be either a string or regular expression
    
    '''
    if is_string(old):
        text = text.replace(old, new)
    else:
        text = old.sub(new, text)
    
    if strip:
        text = text.strip(None if strip == True else strip)
    
    return text


#-------------------------------------------------------------------------------
def remove(text, what, strip=False):
    return replace(text, what, '', strip=strip)


#-------------------------------------------------------------------------------
def replace_all(text, items):
    for a,b in items:
        text = replace(text, a, b)
    return text


#-------------------------------------------------------------------------------
def remove_all(text, items, strip=False):
    for item in items:
        text = remove(text, item, strip=strip)
    return text


#-------------------------------------------------------------------------------
def splitter(text, tok, expected=2, default=None, strip=False):
    bits = text.split(tok, expected - 1)
    if strip:
        bits = [s.strip() for s in bits]
    
    n = len(bits)
    while n < expected:
        bits.append(default)
        n += 1
    
    return bits


#-------------------------------------------------------------------------------
def clean_html_entities(text):
    return replace_all(text,
        ('&amp;', '&'),
        ('&nbsp;', ' '),
    )


#-------------------------------------------------------------------------------
def matches(text, what):
    if is_string(what):
        return text.find(what) > -1
    elif callable(what):
        return what(text)
    return what.match(text)


#-------------------------------------------------------------------------------
def beautiful_results(results):
    soup = bs4.BeautifulSoup()
    soup.contents = results
    return soup


#===============================================================================
class Bits(object):

    #---------------------------------------------------------------------------
    def __init__(self, data=''):
        self._data = data
        self._stack = []
    
    #---------------------------------------------------------------------------
    def __str__(self):
        return self._data
    
    __unicode__ = __str__
    
    #---------------------------------------------------------------------------
    def __len__(self):
        return len(self._data)
    
    #---------------------------------------------------------------------------
    def __iter__(self):
        return iter(self._data)

    #---------------------------------------------------------------------------
    def _update(self, data):
        self._stack.append(self._data)
        self._data = data
    
    #---------------------------------------------------------------------------
    def serialize(self, results, format='python', variable='data'):
        if format == 'python':
            if isinstance(results, (list, tuple)):
                results = pformat(results)
            else:
                results = "'''{}'''".format(results)

            return '{} = {}'.format(variable, results)
        
        raise ValueError('Unknown serialization format: {}'.format(format))
    
    #---------------------------------------------------------------------------
    @property
    def text(self):
        return Text(unicode(self))

    #---------------------------------------------------------------------------
    @property
    def lines(self):
        return Lines(unicode(self))

    #---------------------------------------------------------------------------
    @property
    def html(self):
        return HTML(unicode(self))
    
    #---------------------------------------------------------------------------
    def end(self):
        self._data = self._stack.pop()
        return self

    #---------------------------------------------------------------------------
    @classmethod
    def combine(cls, contents):
        if not contents:
            return Bits()
            
        c = contents[0]
        if isinstance(c, Lines):
            lines = []
            for li in contents:
                lines.extend(li._data)
            return Lines(lines)
        elif isinstance(c, HTML):
            soup = bs4.BeautifulSoup()
            for doc in contents:
                soup.contents.extend(doc.body())
            return HTML(soup)
        else:
            return Text('\n'.join(item._data for item in contents))


#===============================================================================
class Text(Bits):
    '''
    Text handler class for manipulating a block text.
    '''
    
    #---------------------------------------------------------------------------
    def __iter__(self):
        return iter(self._data.splitlines())
    
    #---------------------------------------------------------------------------
    def remove_all(self, what, **kws):
        self._update(remove_all(self._data, what, **kws))
        return self
        
    #---------------------------------------------------------------------------
    def replace_all(self, items, **kws):
        self._update(replace_all(self._data, items, **kws))
        return self


#===============================================================================
class HTML(Bits):

    BAD_ATTRS = 'align alink background bgcolor border clear height hspace language link nowrap start text type valign vlink vspace width'.split()
    
    #---------------------------------------------------------------------------
    def __init__(self, data):
        if is_string(data):
            data = bs4.BeautifulSoup(data)
        super(HTML, self).__init__(data)

    #---------------------------------------------------------------------------
    def __unicode__(self):
        return markup.bs4format(self._data)
    
    __str__ = __unicode__

    #---------------------------------------------------------------------------
    def get_copy(self):
        return bs4.BeautifulSoup(unicode(self._data))
        #return copy.deepcopy(self._data)
    
    #---------------------------------------------------------------------------
    def _call_cmd(self, cmd, args):
        if utils.is_string(args):
            args = args.split(',')
        
        soup = self.get_copy()
        for arg in args:
            for el in soup.select(arg):
                method = getattr(el, cmd)
                method()
                
        self._update(soup)
        return self
    
    #---------------------------------------------------------------------------
    def unwrap(self, tags):
        return self._call_cmd('unwrap', tags)
    
    #---------------------------------------------------------------------------
    def replace_with(self, query, what):
        soup = self.get_copy()
        for el in soup.select(query):
            el.replace_with(what)
        
        self._update(soup)
        return self
        
    #---------------------------------------------------------------------------
    def extract(self, tags):
        return self._call_cmd('extract', tags)
    
    #---------------------------------------------------------------------------
    def select(self, query):
        results = self._data.select(query)
        verbose('Selected {} matches', len(results))
        if results:
            self._update(beautiful_results(results))

        return self

    #---------------------------------------------------------------------------
    def select_attr(self, query, attr, test=bool):
        results = []
        for el in self._data.select(query):
            if el.attrs and attr in el.attrs:
                value = el.attrs[attr]
                if test(value):
                    results.append(value)

        return Lines(results)

    #---------------------------------------------------------------------------
    def remove_attrs(self, attrs=None):
        if utils.is_string(attrs):
            attrs = attrs if attrs == '*' else attrs.split(',')

        attrs = attrs or HTML.BAD_ATTRS
        soup = self.get_copy()
        for el in soup.descendants:
            if hasattr(el, 'attrs'):
                if attrs == '*':
                    el.attrs = {}
                elif el.attrs:
                    el.attrs = dict([(k, v) for k,v in el.attrs.items() if k not in attrs])
        
        self._update(soup)
        return self

    #---------------------------------------------------------------------------
    def serialize(self, query): # query):
        results = []
        # for item in self._data.select(query):
        #     results.append([i.strip() for i in item.strings])
        
        current = results
        for item in self._data.select(query):
            values = []
            results.append(values)
            for content in item.contents:
                if isinstance(content, bs4.NavigableString):
                    content = content.strip()
                    if content:
                        values.append(content)
                else:
                    content = content.string
                    values.append(content.strip() if content else '')
        
        return super(HTML, self).serialize(results)

    #---------------------------------------------------------------------------
    def collapse(self, query, joiner=' '):
        soup = self.get_copy()
        for item in soup.select(query):
            item.string = joiner.join([s.strip() for s in item.text.split()])
            
        self._update(soup)
        return self

#===============================================================================
class Lines(Bits):
    '''
    Convenience class for manipulating and traversing lines of text.
    '''
    #---------------------------------------------------------------------------
    def __init__(self, data):
        if utils.is_string(data):
            data = data.splitlines()
        super(Lines, self).__init__(data)

    #---------------------------------------------------------------------------
    def _find_first(self, what):
        for i, line in enumerate(self._data):
            if matches(line, what):
                return i
        
    #---------------------------------------------------------------------------
    def __str__(self):
        return u'\n'.join(self._data)
    
    __unicode__ = __str__
    
    #---------------------------------------------------------------------------
    def format(self, fmt):
        self._update([fmt.format(l) for l in self._data])
        return self
    
    #---------------------------------------------------------------------------
    def compress(self):
        self._update([' '.join(l.strip().split()) for l in self._data])
        return self
    
    #---------------------------------------------------------------------------
    def strip(self):
        self._update([l.strip() for l in self._data])
        return self
        
    #---------------------------------------------------------------------------
    def skip_to(self, what, keep=True):
        found = self._find_first(what)
        if found is not None:
            self._update(self._data[found:])
        
        return self
        
    #----------------------------------------------------------------------------
    def read_until(self, what, keep=True):
        found = self._find_first(what)
        if found is not None:
            found = found + 1 if keep else found
            self._update(self._data[:found])
        
        return self
        
    #---------------------------------------------------------------------------
    def matches(self, what):
        self._update([l for l in self._data if matches(l, what)])
        return self
