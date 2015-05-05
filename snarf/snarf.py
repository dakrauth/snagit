# -*- coding:utf8 -*-
import re
import os
import codecs
from collections import deque

try:
    import requests
except ImportError:
    import warnings
    warning.warn('Missing `requests` installation', ImportWarning)
    
    #---------------------------------------------------------------------------
    def read_url(*args, **kws):
        raise RuntimeError('Unavailable - check environment for proper 3rd party installs')
    
else:

    #---------------------------------------------------------------------------
    def read_url(url, as_text=True):
        r = requests.get(url)
        return r.text if as_text else r.content


VERSION = (0, 1)

#-------------------------------------------------------------------------------
def get_version():
    return '.'.join(map(str, VERSION))


#-------------------------------------------------------------------------------
def read_file(filename, encoding='utf8'):
    with open(filename, 'r', encoding=encoding) as fp:
        return fp.read()


#-------------------------------------------------------------------------------
def is_string(obj):
    '''
    Check if obj is a string
    '''
    return isinstance(obj, basestring)


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
def replace_all(text, *items):
    for a,b in items:
        text = replace(text, a, b)
    return text


#-------------------------------------------------------------------------------
def remove_all(text, *items, **kws):
    strip = kws.get('strip', False)
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
class Text(object):
    '''
    Text handler class for manipulating a block text/HTML.
    '''

    BAD_ATTRS = 'align alink background bgcolor border clear height hspace language link nowrap start text type valign vlink vspace width'.split()

    #---------------------------------------------------------------------------
    def __init__(self, text, normalize=False, bad_attrs=False):
        self.text = text
        if normalize:
            self.normalize()
        
        if bad_attrs:
            self.remove_attrs()
    
    #---------------------------------------------------------------------------
    def __str__(self):
        return self.text
    
    #---------------------------------------------------------------------------
    def lines(self):
        return Lines(self.text)
    
    #---------------------------------------------------------------------------
    def normalize(self):
        '''
        Convert all single quoted tag attributes to double quotes
        '''
        self.text = re.sub(
            r" ([\w_-]+)='([^']*)'", r' \1="\2"',
            self.text,
            flags=re.IGNORECASE
        )
        return self
        
    #---------------------------------------------------------------------------
    def remove_attrs(self, attrs=None):
        attrs = '|'.join(attrs or self.BAD_ATTRS)
        self.text = replace(
            self.text,
            re.compile(' (' + attrs + ')="[^"]*"', flags=re.IGNORECASE),
            ''
        )
        return self
    
    #---------------------------------------------------------------------------
    def remove_all(self, *what, **kws):
        self.text = remove_all(self.text, *what, **kws)
        return self

    #---------------------------------------------------------------------------
    def replace_all(self, *items, **kws):
        self.text = replace_all(self.text, *items, **kws)
        return self
        
    #---------------------------------------------------------------------------
    def remove_tags(self, *tags):
        for tag in tags:
            tag_re = re.compile(r'</?%s(>| [^>]*>)' % tag, re.IGNORECASE)
            self.text = replace(self.text, tag_re, '')
        return self


#===============================================================================
class Lines(object):
    '''
    Convenience class for manipulating and traversing lines of text.
    '''
    #---------------------------------------------------------------------------
    def __init__(self, text):
        self.lines = text.splitlines()
        self.stack = deque()

    #---------------------------------------------------------------------------
    def _find_first(self, what):
        for i, line in enumerate(self.lines):
            if matches(line, what):
                return i

    #---------------------------------------------------------------------------
    def _update(self, start=None, end=None):
        if start == end == None:
            return
        
        self.stack.append(self.lines[end:start])
        self.lines = self.lines[start:end]
        
    #---------------------------------------------------------------------------
    def __str__(self):
        return self.text
    
    #---------------------------------------------------------------------------
    def end(self):
        self.lines = self.stack.pop()
        return self
    
    #---------------------------------------------------------------------------
    @property
    def text(self):
        return '\n'.join(self.lines)
    
    #---------------------------------------------------------------------------
    def compress(self):
        self.lines = [' '.join(l.strip().split()) for l in self.lines]
        return self
    
    #---------------------------------------------------------------------------
    def strip(self):
        self.lines = [l.strip() for l in self.lines]
        return self

    #---------------------------------------------------------------------------
    def skip_to(self, what, keep=True):
        found = self._find_first(what)
        if found is not None:
            found = found if keep else found + 1
            self._update(start=found)
        
        return self

    #----------------------------------------------------------------------------
    def read_until(self, what, keep=True):
        found = self._find_first(what)
        if found is not None:
            found = found + 1 if keep else found
            self._update(end=found)
        
        return self

