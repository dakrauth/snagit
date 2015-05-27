# -*- coding:utf8 -*-
import re
import os
import json
from pprint import pformat
from bs4 import BeautifulSoup, NavigableString
from . import utils
from . import markup

verbose = utils.verbose
is_string = utils.is_string

BAD_ATTRS = 'align alink background bgcolor border clear height hspace language link nowrap start text type valign vlink vspace width'.split()


#-------------------------------------------------------------------------------
def is_lines(what):
    return isinstance(what, (list, tuple))


#-------------------------------------------------------------------------------
def is_soup(what):
    return isinstance(what, BeautifulSoup)


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
def find_first(data, what):
    for i, line in enumerate(data):
        if matches(line, what):
            return i


#-------------------------------------------------------------------------------
def beautiful_results(results):
    '''
    Convert a list of HTML elements back into a ``BeautifulSoup`` instance.
    
    For example, ``results`` would be the expected return from ``soup.select``
    or ``soup.find_all``.
    '''
    soup = BeautifulSoup()
    soup.contents = results
    return soup


#===============================================================================
class Bits(object):
    
    #---------------------------------------------------------------------------
    def __iter__(self):
        return iter(self._data)

    #---------------------------------------------------------------------------
    def __len__(self):
        return len(self._data)

    #---------------------------------------------------------------------------
    def serialize(self, format):
        data = unicode(self._data)
        return "'''{}'''".format(data) if format == 'python' else data

    #---------------------------------------------------------------------------
    def __str__(self):
        return unicode(self)
    
    #---------------------------------------------------------------------------
    def __getattr__(self, attr):
        return getattr(self._data, attr)


#===============================================================================
class Text(Bits):
    '''
    Handler class for manipulating a block text.
    '''
    #---------------------------------------------------------------------------
    def __init__(self, data):
        self._data = unicode(data)
        
    #---------------------------------------------------------------------------
    def __iter__(self):
        return iter(self._data.splitlines())
        
    #---------------------------------------------------------------------------
    def __unicode__(self):
        return self._data


#===============================================================================
class HTML(Bits):
    '''
    Handler for manipulating a block of HTML. A wrapper for ``BeautifulSoup``.
    '''
    
    #---------------------------------------------------------------------------
    def __init__(self, data):
        self._data = data if is_soup(data) else BeautifulSoup(unicode(data))

    #---------------------------------------------------------------------------
    def __unicode__(self):
        return markup.bs4format(self._data)
    
    #---------------------------------------------------------------------------
    def serialize(self, format):
        results = []
        for item in self._data.findChildren(recursive=False):
            values = []
            results.append(values)
            for content in item.contents:
                if isinstance(content, NavigableString):
                    content = content.strip()
                    if content:
                        values.append(content)
                else:
                    content = content.string
                    values.append(content.strip() if content else '')

        return pformat(results)

#===============================================================================
class Lines(Bits):
    '''
    Handler class for manipulating and traversing lines of text.
    '''
    #---------------------------------------------------------------------------
    def __init__(self, data):
        self._data = data[:] if is_lines(data) else unicode(data).splitlines()

    #---------------------------------------------------------------------------
    def __unicode__(self):
        return u'\n'.join(self._data)

    #---------------------------------------------------------------------------
    def serialize(self, format):
        return pformat(self._data)


#===============================================================================
class Content(object):

    #---------------------------------------------------------------------------
    def __init__(self, data=''):
        self._stack = []
        self._data = self._handler(data)

    #---------------------------------------------------------------------------
    def _handler(self, data):
        if is_lines(data):
            return Lines(data)
        elif is_soup(data):
            return HTML(data)
        elif is_string(data):
            return Text(data)
        else:
            raise ValueError('Cannot handle data type, must be string or list')
    
    #---------------------------------------------------------------------------
    def __unicode__(self):
        return unicode(self._data)
    
    #---------------------------------------------------------------------------
    def __iter__(self):
        return iter(self._data)

    #---------------------------------------------------------------------------
    @property
    def data(self):
        return self._data._data
    
    #---------------------------------------------------------------------------
    def _update(self, data):
        self._stack.append(self._data)
        self._data = self._handler(data)
    
    #---------------------------------------------------------------------------
    @property
    def text(self):
        return unicode(self._data)

    #---------------------------------------------------------------------------
    @property
    def lines(self):
        return unicode(self._data).splitlines()

    #---------------------------------------------------------------------------
    @property
    def soup(self):
        return BeautifulSoup(unicode(self._data))

    #---------------------------------------------------------------------------
    def end(self):
        self._data = self._stack.pop()

    #---------------------------------------------------------------------------
    @classmethod
    def combine(cls, contents):
        '''
        Distill contents into a single piece of content.
        '''
        if not contents:
            return Content('')
            
        c = contents[0]._data
        if isinstance(c, Lines):
            lines = []
            for li in contents:
                lines.extend(li._data)
            return Content(lines)
        elif isinstance(c, HTML):
            soup = BeautifulSoup()
            for doc in contents:
                soup.contents.extend(doc.body())
            return Content(soup)
        else:
            return Content('\n'.join(item._data for item in contents))
            
    #---------------------------------------------------------------------------
    def remove_each(self, items, **kws):
        self._update(remove_each(self.text, items, **kws))
        
    #---------------------------------------------------------------------------
    def replace_each(self, items, **kws):
        self._update(replace_each(self.text, items, **kws))
        
    #---------------------------------------------------------------------------
    def _call_cmd(self, cmd, args):
        if is_string(args):
            args = args.split(',')
        
        soup = self.soup
        for item in args:
            for el in soup.select(item):
                method = getattr(el, cmd)
                method()
                
        self._update(soup)
    
    #---------------------------------------------------------------------------
    def unwrap(self, tags):
        self._call_cmd('unwrap', tags)

    #---------------------------------------------------------------------------
    def extract(self, tags):
        self._call_cmd('extract', tags)
    
    #---------------------------------------------------------------------------
    def replace_with(self, query, what):
        soup = self.soup
        for el in soup.select(query):
            el.replace_with(what)
        
        self._update(soup)
        
    #---------------------------------------------------------------------------
    def select(self, query):
        results = self._data.select(query)
        verbose('Selected {} matches', len(results))
        if results:
            self._update(beautiful_results(results))

    #---------------------------------------------------------------------------
    def select_attr(self, query, attr, test=bool):
        results = []
        for el in self._data.select(query):
            if el.attrs and attr in el.attrs:
                value = el.attrs[attr]
                if test(value):
                    results.append(value)

        self._update(results)

    #---------------------------------------------------------------------------
    def remove_attrs(self, attrs=None):
        if is_string(attrs):
            attrs = attrs if attrs == '*' else attrs.split(',')

        attrs = attrs or BAD_ATTRS
        soup = self.soup
        for el in soup.descendants:
            if hasattr(el, 'attrs'):
                if attrs == '*':
                    el.attrs = {}
                elif el.attrs:
                    el.attrs = dict([(k, v) for k,v in el.attrs.items() if k not in attrs])
        
        self._update(soup)

    #---------------------------------------------------------------------------
    def serialize(self, format='python', variable='data'):
        if format == 'python':
            text = '{} = {}'.format(variable, self._data.serialize(format))
        elif format == 'json':
            text = json.dumps(self._data.serialize(format))
        else:
            raise ValueError('Unknown serialization format: {}'.format(format))
            
        self._update(text)

    #---------------------------------------------------------------------------
    def collapse(self, query, joiner=' '):
        soup = self.soup
        for item in soup.select(query):
            item.string = joiner.join([s.strip() for s in item.text.split()])
            
        self._update(soup)

    #---------------------------------------------------------------------------
    def format(self, fmt):
        self._update([fmt.format(l) for l in self.lines])
    
    #---------------------------------------------------------------------------
    def compress(self):
        self._update([' '.join(l.strip().split()) for l in self.lines])
    
    #---------------------------------------------------------------------------
    def strip(self):
        self._update([l.strip() for l in self.lines])
        
    #---------------------------------------------------------------------------
    def skip_to(self, what, keep=True):
        lines = self.lines
        found = find_first(lines, what)
        if found is not None:
            if not keep:
                found += 1
            
            self._update(lines[found:])
        
    #----------------------------------------------------------------------------
    def read_until(self, what, keep=True):
        lines = self.lines
        found = find_first(lines, what)
        if found is not None:
            if keep:
                found += 1
            
            self._update(lines[:found])
        
    #---------------------------------------------------------------------------
    def matches(self, what):
        self._update([l for l in self.lines if matches(l, what)])
