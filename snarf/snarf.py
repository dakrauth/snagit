# -*- coding:utf8 -*-
import re
import os
from collections import deque

from . import utils
is_string = utils.is_string

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


#===============================================================================
class Bits(object):

    #---------------------------------------------------------------------------
    def __init__(self, data):
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
    def _update(self, data):
        self._stack.append(self._data)
        self._data = data
    
    #---------------------------------------------------------------------------
    def end(self):
        self._data = self._stack.pop()
        return self


#===============================================================================
class Text(Bits):
    '''
    Text handler class for manipulating a block text/HTML.
    '''

    BAD_ATTRS = 'align alink background bgcolor border clear height hspace language link nowrap start text type valign vlink vspace width'.split()

    #---------------------------------------------------------------------------
    def __init__(self, text):
        super(Text, self).__init__(text)
    
    #---------------------------------------------------------------------------
    def lines(self):
        return Lines(self._data)
    
    #---------------------------------------------------------------------------
    def normalize(self):
        '''
        Convert all single quoted tag attributes to double quotes
        '''
        self._update(normalize_attrs(self._data))
        return self
        
    #---------------------------------------------------------------------------
    def remove_attrs(self, attrs=None):
        if utils.is_string(attrs):
            attrs = attrs.split(',')
        
        attrs = '|'.join(attrs or self.BAD_ATTRS)
        self._update(replace(
            self._data,
            re.compile(' (' + attrs + ')="[^"]*"', flags=re.IGNORECASE),
            ''
        ))
        return self
    
    #---------------------------------------------------------------------------
    def remove_all(self, what, **kws):
        self._update(remove_all(self._data, what, **kws))
        return self

    #---------------------------------------------------------------------------
    def replace_all(self, items, **kws):
        self._update(replace_all(self._data, items, **kws))
        return self
        
    #---------------------------------------------------------------------------
    def remove_tags(self, tags):
        if utils.is_string(tags):
            tags = tags.split(',')

        data = self._data
        for tag in tags:
            tag_re = re.compile(r'</?%s(>| [^>]*>)' % tag, re.IGNORECASE)
            data = replace(self._data, tag_re, '')
            
        self._update(data)
        return self


#===============================================================================
class Lines(Bits):
    '''
    Convenience class for manipulating and traversing lines of text.
    '''
    #---------------------------------------------------------------------------
    def __init__(self, text):
        super(Lines, self).__init__(text.splitlines())

    #---------------------------------------------------------------------------
    def _find_first(self, what):
        for i, line in enumerate(self._data):
            if matches(line, what):
                return i

    #---------------------------------------------------------------------------
    def __str__(self):
        return '\n'.join(self._data)

    __unicode__ = __str__
    
    #---------------------------------------------------------------------------
    @property
    def text(self):
        return Text(unicode(self))
    
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
