# -*- coding:utf8 -*-
import re
import os
import json
from pprint import pformat
#import copy

try:
    import bs4
except ImportError:
    bs4 = None

from . import utils
from . import markup

is_string = utils.is_string
verbose = utils.verbose


#-------------------------------------------------------------------------------
def replace(text, old, new, count=None, strip=False):
    '''
    Replace an ``old`` subset of ``text`` with ``new``.
    
    ``old`` type may be either a string or regular expression.
    
    If ``strip``, remove all leading/trailing whitespace.
    
    If ``count``, replace the specified number of occurence, otherwise replace all.
    '''
    if is_string(old):
        text = text.replace(old, new, -1 if count is None else count)
    else:
        text = old.sub(new, text, 0 if count is None else count)
    
    if strip:
        text = text.strip(None if strip == True else strip)
    
    return text


#-------------------------------------------------------------------------------
def remove(text, what, count=None, strip=False):
    '''
    Like ``replace``, where ``new`` replacement is an empty string.
    '''
    return replace(text, what, '', strip=strip)


#-------------------------------------------------------------------------------
def replace_each(text, items, count=None, strip=False):
    '''
    Like ``replace``, where each occurrence in ``items`` is a 2-tuple of 
    ``(old, new)`` pair.
    '''
    for a,b in utils.seq(items):
        text = replace(text, a, b, count=count, strip=strip)
    return text


#-------------------------------------------------------------------------------
def remove_each(text, items, count=None, strip=False):
    '''
    Like ``remove``, where each occurrence in ``items`` is ``what`` to remove.
    '''
    for item in utils.seq(items):
        text = remove(text, item, count=count, strip=strip)
    return text


#-------------------------------------------------------------------------------
def splitter(text, token, expected=2, default=None, strip=False):
    '''
    Split ``text`` by ``token`` into at least ``expected`` number of results.
    
    If actual number of results is less than ``expected``, pad with ``default``.
    
    If ``strip``, than do just that to each result.
    '''
    bits = text.split(token, expected - 1)
    if strip:
        bits = [s.strip() for s in bits]
    
    n = len(bits)
    while n < expected:
        bits.append(default)
        n += 1
    
    return bits


#-------------------------------------------------------------------------------
def matches(text, what):
    '''
    Check if ``what`` occurs in ``text``
    
    TODO: not sure if ``matches`` is appropriate, maybe ``contains``?
    '''
    if is_string(what):
        return text.find(what) > -1
    elif callable(what):
        return what(text)
    return what.match(text)


#-------------------------------------------------------------------------------
def beautiful_results(results):
    '''
    Convert a list of HTML elements back into a ``BeautifulSoup`` instance.
    
    For example, ``results`` would be the expected return from ``soup.select``
    or ``soup.find_all``.
    '''
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
        
        elif format == 'json':
            return json.dumps(results)
            
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
    Handler class for manipulating a block text.
    '''
    
    #---------------------------------------------------------------------------
    def __iter__(self):
        return iter(self._data.splitlines())
    
    #---------------------------------------------------------------------------
    def remove_each(self, items, **kws):
        self._update(remove_each(self._data, items, **kws))
        return self
        
    #---------------------------------------------------------------------------
    def replace_each(self, items, **kws):
        self._update(replace_each(self._data, items, **kws))
        return self


#===============================================================================
class HTML(Bits):
    '''
    Handler for manipulating a block of HTML. A wrapper for ``BeautifulSoup``.
    '''
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
    @property
    def soup(self):
        return bs4.BeautifulSoup(unicode(self._data))
        #return copy.deepcopy(self._data)
    
    #---------------------------------------------------------------------------
    def _call_cmd(self, cmd, args):
        if is_string(args):
            args = args.split(',')
        
        soup = self.soup
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
        soup = self.soup
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
        if is_string(attrs):
            attrs = attrs if attrs == '*' else attrs.split(',')

        attrs = attrs or HTML.BAD_ATTRS
        soup = self.soup
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
        soup = self.soup
        for item in soup.select(query):
            item.string = joiner.join([s.strip() for s in item.text.split()])
            
        self._update(soup)
        return self


#===============================================================================
class Lines(Bits):
    '''
    Handler class for manipulating and traversing lines of text.
    '''
    #---------------------------------------------------------------------------
    def __init__(self, data):
        if is_string(data):
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
            if not keep:
                found += 1
            self._update(self._data[found:])
        
        return self
        
    #----------------------------------------------------------------------------
    def read_until(self, what, keep=True):
        found = self._find_first(what)
        if found is not None:
            if keep:
                found += 1
            self._update(self._data[:found])
        
        return self
        
    #---------------------------------------------------------------------------
    def matches(self, what):
        self._update([l for l in self._data if matches(l, what)])
        return self
