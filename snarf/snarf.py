# -*- coding:utf8 -*-
from __future__ import unicode_literals
import re
import os
import six
import json
from pprint import pformat
import bs4 as beautiful_soup
from . import utils
from . import markup
import strutil

if six.PY2:
    str = unicode


verbose = utils.verbose
is_string = strutil.is_string

BAD_ATTRS = 'align alink background bgcolor border clear height hspace language link nowrap start text type valign vlink vspace width'.split()


#-------------------------------------------------------------------------------
def is_lines(what):
    return isinstance(what, (list, tuple))


#-------------------------------------------------------------------------------
def is_soup(what):
    return isinstance(what, (beautiful_soup.BeautifulSoup, beautiful_soup.PageElement))


#-------------------------------------------------------------------------------
def is_navigable_string(what):
    return isinstance(what, beautiful_soup.NavigableString)


#-------------------------------------------------------------------------------
def make_soup(markup=''):
    return beautiful_soup.BeautifulSoup(markup, 'html.parser')


#-------------------------------------------------------------------------------
def beautiful_results(results):
    '''
    Convert a list of HTML elements back into a ``BeautifulSoup`` instance.
    
    For example, ``results`` would be the expected return from ``soup.select``
    or ``soup.find_all``.
    '''
    soup = make_soup()
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
        data = str(self._data)
        return "'''{}'''".format(data) if format == 'python' else data

    #---------------------------------------------------------------------------
    def __getattr__(self, attr):
        return getattr(self._data, attr)

    #---------------------------------------------------------------------------
    @staticmethod
    def create(data, guess=False):
        if is_lines(data):
            return Lines(data)
        elif is_soup(data):
            return Soup(data)
        elif is_string(data):
            if guess:
                c = content.strip()
                if c.startswith('<') and c.endswith('>'):
                    return Soup(data)
            return Text(data)
            
        raise ValueError('Cannot create data type, must be string or list')


#===============================================================================
@six.python_2_unicode_compatible
class Text(Bits):
    '''
    Handler class for manipulating a block text.
    '''
    #---------------------------------------------------------------------------
    def __init__(self, data):
        self._data = data
        
    #---------------------------------------------------------------------------
    def __iter__(self):
        return iter(self._data.splitlines())
        
    #---------------------------------------------------------------------------
    def __str__(self):
        return self._data


#===============================================================================
@six.python_2_unicode_compatible
class Soup(Bits):
    '''
    Handler for manipulating a block of HTML. A wrapper for ``BeautifulSoup``.
    '''
    
    #---------------------------------------------------------------------------
    def __init__(self, data):
        self._data = data if is_soup(data) else make_soup(str(data))

    #---------------------------------------------------------------------------
    def __str__(self):
        return markup.format(self._data)
    
    #---------------------------------------------------------------------------
    def serialize(self, format):
        results = []
        for item in self._data.findChildren(recursive=False):
            values = []
            results.append(values)
            for content in item.contents:
                if is_navigable_string(content):
                    content = content.strip()
                    if content:
                        values.append(content)
                else:
                    content = content.string
                    values.append(content.strip() if content else '')

        return pformat(results)

#===============================================================================
@six.python_2_unicode_compatible
class Lines(Bits):
    '''
    Handler class for manipulating and traversing lines of text.
    '''
    #---------------------------------------------------------------------------
    def __init__(self, data):
        self._data = data[:] if is_lines(data) else str(data).splitlines()

    #---------------------------------------------------------------------------
    def __str__(self):
        return '\n'.join(self._data)

    #---------------------------------------------------------------------------
    def serialize(self, format):
        return pformat(self._data)


#===============================================================================
@six.python_2_unicode_compatible
class Content(object):

    #---------------------------------------------------------------------------
    def __init__(self, data='', guess=False):
        self._data = Bits.create(data, guess)
    
    #---------------------------------------------------------------------------
    def __repr__(self):
        return 'Content({})'.format(self._data.__class__.__name__)
    
    #---------------------------------------------------------------------------
    def __str__(self):
        return str(self._data)
    
    #---------------------------------------------------------------------------
    def __iter__(self):
        return iter(self._data)
    
    #---------------------------------------------------------------------------
    def text(self):
        return str(self)
    
    #---------------------------------------------------------------------------
    def lines(self):
        return str(self).splitlines()
    
    #---------------------------------------------------------------------------
    def soup(self):
        return make_soup(str(self))
    
    #---------------------------------------------------------------------------
    def remove_each(self, items, **kws):
        return Content(strutil.remove_each(self.text(), items, **kws))
    
    #---------------------------------------------------------------------------
    def replace_each(self, items, **kws):
        return Content(strutil.replace_each(self.text(), items, **kws))
    
    #---------------------------------------------------------------------------
    def _call_cmd(self, cmd, args):
        if is_string(args):
            args = args.split(',')
        
        soup = self.soup()
        for item in args:
            for el in soup.select(item):
                method = getattr(el, cmd)
                method()
                
        return Content(soup)
    
    #---------------------------------------------------------------------------
    def unwrap(self, tags):
        return self._call_cmd('unwrap', tags)
    
    #---------------------------------------------------------------------------
    def unwrap_attr(self, query, attr):
        soup = self.soup()
        for el in soup.select(query):
            el.replace_with(getattr(el, 'attrs', {}).get(attr, ''))
            
        return Content(soup)
        
    #---------------------------------------------------------------------------
    def extract(self, tags):
        return self._call_cmd('extract', tags)
    
    #---------------------------------------------------------------------------
    def replace_with(self, query, what):
        soup = self.soup()
        for el in soup.select(query):
            el.replace_with(what)
        
        return Content(soup)
        
    #---------------------------------------------------------------------------
    def select(self, query):
        results = self.soup().select(query)
        verbose('Selected {} matches', len(results))
        return Content(beautiful_results(results)) if results else self

    #---------------------------------------------------------------------------
    def select_attr(self, query, attr, test=bool):
        results = []
        for el in self.soup().select(query):
            if el.attrs and attr in el.attrs:
                value = el.attrs[attr]
                if test(value):
                    results.append(value)

        return Content(results)

    #---------------------------------------------------------------------------
    def remove_attrs(self, attrs=None):
        if is_string(attrs):
            attrs = attrs if attrs == '*' else attrs.split(',')

        attrs = attrs or BAD_ATTRS
        soup = self.soup()
        for el in soup.descendants:
            if hasattr(el, 'attrs'):
                if attrs == '*':
                    el.attrs = {}
                elif el.attrs:
                    el.attrs = dict([(k, v) for k,v in el.attrs.items() if k not in attrs])
        
        return Content(soup)

    #---------------------------------------------------------------------------
    def serialize(self, format='python', variable='data'):
        if format == 'python':
            text = '{} = {}'.format(variable, self._data.serialize(format))
        elif format == 'json':
            text = json.dumps(self._data.serialize(format))
        else:
            raise ValueError('Unknown serialization format: {}'.format(format))
            
        return Content(text)

    #---------------------------------------------------------------------------
    def collapse(self, query, joiner=' '):
        soup = self.soup()
        for item in soup.select(query):
            bits = list(i.strip() for i in item.stripped_strings)
            item.string = joiner.join(bits)
            
        return Content(soup)

    #---------------------------------------------------------------------------
    def format(self, fmt):
        return Content([fmt.format(l) for l in self.lines()])
    
    #---------------------------------------------------------------------------
    def compress(self):
        return Content([' '.join(l.strip().split()) for l in self.lines()])
    
    #---------------------------------------------------------------------------
    def strip(self):
        return Content([l.strip() for l in self.lines()])
        
    #---------------------------------------------------------------------------
    def skip_to(self, what, keep=True):
        lines = self.lines()
        found = strutil.find_first(lines, what)
        if found is not None:
            if not keep:
                found += 1
            
            return Content(lines[found:])

        return self
        
    #----------------------------------------------------------------------------
    def read_until(self, what, keep=True):
        lines = self.lines()
        found = strutil.find_first(lines, what)
        if found is not None:
            if keep:
                found += 1
            
            return Content(lines[:found])

        return self

    #---------------------------------------------------------------------------
    def matches(self, what):
        return Content([l for l in self.lines() if strutil.matches(l, what)])


#===============================================================================
@six.python_2_unicode_compatible
class Contents(object):
    
    #---------------------------------------------------------------------------
    def __init__(self, contents=None, guess=False):
        self.stack = []
        self.set_contents(contents, guess=guess)
    
    #---------------------------------------------------------------------------
    def __iter__(self):
        return iter(self.contents)
    
    #---------------------------------------------------------------------------
    def __len__(self):
        return len(self.contents)
    
    #---------------------------------------------------------------------------
    def __str__(self):
        return '\n'.join([str(c) for c in self])
    
    #---------------------------------------------------------------------------
    def __getitem__(self, index):
        return self.contents[index]
    
    #---------------------------------------------------------------------------
    def end(self):
        self.contents = self.stack.pop()
    
    #---------------------------------------------------------------------------
    def update(self, contents):
        if self.contents:
            self.stack.append(self.contents)
        self.set_contents(contents)
    
    #---------------------------------------------------------------------------
    def __getattr__(self, attr):
        if not hasattr(Content, attr):
            raise AttributeError('Unknown attribute "{}"'.format(attr))
            
        def handler(*args, **kws):
            contents = []
            for ct in self.contents:
                fn = getattr(ct, attr)
                result = fn(*args, **kws)
                contents.append(result)
            self.update(contents)
        return handler

    #---------------------------------------------------------------------------
    def data_merge(self):
        data = None
        if self.contents:
            ct = self.contents[0]._data
            if isinstance(ct, Lines):
                data = []
                for ct in self.contents:
                    data.extend(ct._data)
            elif isinstance(ct, Soup):
                data = make_soup()
                for ct in self.contents:
                    data.contents.extend(ct._data.body())
            else:
                data = str(self)
        
        return data
    
    #---------------------------------------------------------------------------
    def combine(self):
        '''
        Distill contents into a single piece of content.
        '''
        if self.contents:
            data = self.data_merge()
            self.update([Content(data)])
        
    #---------------------------------------------------------------------------
    def set_contents(self, contents, guess=False):
        self.contents = []
        if contents:
            for content in contents:
                if not isinstance(content, Content):
                    content = Content(content, guess=guess)
                        
                self.contents.append(content)
