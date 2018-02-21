# -*- coding:utf8 -*-
import re
import os
import json
import logging
from pprint import pformat

import bs4
import strutil

from . import utils
from . import markup
from . import exceptions

try:
    import lxml.html
    DEFAULT_BS4_FEATRUE = 'lxml'
except ImportError:
    try:
        import html5lib
        DEFAULT_BS4_FEATRUE = 'html5lib'
    except ImportError:
        DEFAULT_BS4_FEATRUE = 'html.parser'

logger = logging.getLogger(__name__)


def is_lines(what):
    return isinstance(what, (list, tuple))


def is_soup(what):
    return isinstance(what, bs4.BeautifulSoup)


def is_element(what):
    return isinstance(what, bs4.PageElement)


def is_navigable_string(what):
    return isinstance(what, bs4.NavigableString)


def make_soup(contents='', feature=None):
    feature = feature or DEFAULT_BS4_FEATRUE
    if isinstance(contents, (str, bytes)):
        return bs4.BeautifulSoup(contents, feature)

    if is_soup(contents):
        contents = contents.contents
    elif is_element(contents):
        contents = [contents]
    elif not isinstance(contents, list):
        raise ValueError('Cannot create soup from type {}'.format(type(contents)))

    soup = bs4.BeautifulSoup('', feature)
    soup.contents.clear()
    for el in contents:
        soup.append(el.__copy__())

    return soup


class Bits:

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def serialize(self, format):
        data = str(self._data)
        return "'''{}'''".format(data) if format == 'python' else data

    def __getattr__(self, attr):
        return getattr(self._data, attr)

    @staticmethod
    def create(data, guess=False):
        if is_lines(data):
            return Lines(data)
        elif is_soup(data):
            return Soup(data)

        if isinstance(data, bytes):
            data = data.decode()

        if strutil.is_string(data):
            if guess:
                c = content.strip()
                if c.startswith('<') and c.endswith('>'):
                    return Soup(data)
            return Text(data)
            
        raise ValueError('Cannot create data type, must be string or list')


class Text(Bits):
    '''
    Handler class for manipulating a block text.
    '''

    def __init__(self, data):
        self._data = data

    def __iter__(self):
        return iter(self._data.splitlines())

    def __str__(self):
        return self._data


class Soup(Bits):
    '''
    Handler for manipulating a block of Soup.
    '''

    def __init__(self, data):
        self._data = data if is_soup(data) else make_soup(str(data))

    def soup(self):
        return make_soup(self._data)

    def __str__(self):
        return markup.format(self._data)

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


class Lines(Bits):
    '''
    Handler class for manipulating and traversing lines of text.
    '''

    def __init__(self, data):
        self._data = data[:] if is_lines(data) else str(data).splitlines()

    def __str__(self):
        return '\n'.join(self._data)

    def serialize(self, format):
        return pformat(self._data)


class SoupContentMixin:

    bad_attrs = utils.get_config('bad_attrs')

    def _invoke_cmd(self, cmd, args):
        if strutil.is_string(args):
            args = args.split(',')
        
        soup = self.soup()
        for item in args:
            for el in soup.select(item):
                method = getattr(el, cmd)
                method()
                
        return Content(make_soup(soup))

    def unwrap(self, tags):
        return self._invoke_cmd('unwrap', tags)

    def unwrap_attr(self, query, attr):
        soup = self.soup()
        for el in soup.select(query):
            el.replace_with(getattr(el, 'attrs', {}).get(attr, ''))
            
        return Content(make_soup(soup))

    def extract(self, tags):
        return self._invoke_cmd('extract', tags)

    def replace_with(self, query, what):
        soup = self.soup()
        for el in soup.select(query):
            el.replace_with(what)
        
        return Content(make_soup(soup))

    def select(self, query, limit=None):
        results = self.soup().select(query, limit=limit)
        logger.debug('Selected {} matches'.format(len(results)))
        return Content(make_soup(results)) if results else self

    def extract_empty(self, args):
        soup = self.soup()
        args = utils.extract_args(args)
        for el in soup.select(args or True):
            if not (any(el.attrs) or any(el.stripped_strings)):
                el.extract()

        return Content(make_soup(soup))

    def remove_attrs(self, attrs=None, query=None):
        attrs_re = utils.normalize_search_attrs(attrs)
        soup = self.soup()

        if query:
            elements = soup.select(query)
        else:
            elements = soup.find_all(True)

        for el in elements:
            el.attrs = {
                k: v for k,v in el.attrs.items()
                if not attrs_re.match(k)
            }
        
        return Content(make_soup(soup))

    def collapse(self, query, joiner=','):
        soup = self.soup()
        for item in soup.select(query):
            item.string = joiner.join(item.stripped_strings)
            
        return Content(make_soup(soup))


class TextContentMixin:

    def remove_each(self, items, **kws):
        return Content(strutil.remove_each(self.text(), items, **kws))

    def replace_each(self, items, **kws):
        return Content(strutil.replace_each(self.text(), items, **kws))

    def compress(self):
        return Content(' '.join(l.strip().split()) for l in self.lines())


class LinesContentMixin:
    
    def format(self, fmt):
        return Content([
            fmt.format(line, lineno)
            for lineno, line in enumerate(self.lines())
        ])

    def strip(self):
        return Content([l.strip() for l in self.lines()])

    def skip_to(self, what, keep=True):
        lines = self.lines()
        found = strutil.find_first(lines, what)
        if found is not None:
            if not keep:
                found += 1
            
            return Content(lines[found:])

        return self

    def read_until(self, what, keep=True):
        lines = self.lines()
        found = strutil.find_first(lines, what)
        if found is not None:
            if keep:
                found += 1
            
            return Content(lines[:found])

        return self

    def matches(self, what):
        return Content([l for l in self.lines() if strutil.matches(l, what)])


class ContentBase(TextContentMixin, SoupContentMixin, LinesContentMixin):

    def __init__(self, data='', guess=False):
        self._data = Bits.create(data, guess)

    def __repr__(self):
        return 'Content({})'.format(self._data.__class__.__name__)

    def __str__(self):
        return str(self._data)

    def __iter__(self):
        return iter(self._data)

    def text(self):
        return str(self)

    def lines(self):
        return str(self).splitlines()

    def soup(self):
        if isinstance(self._data, Soup):
            return self._data.soup()

        return make_soup(str(self))

    def convert(self, convert_to):
        if convert_to == 'text':
            return Content(self.text())
        elif convert_to == 'lines':
            return Content(self.lines())
        elif convert == soup:
            return Content(self.soup())

        return self

    def serialize(self, format='python', variable='data'):
        if format == 'python':
            text = '{} = {}'.format(variable, self._data.serialize(format))
        elif format == 'json':
            text = json.dumps(self._data.serialize(format))
        else:
            raise ValueError('Unknown serialization format: {}'.format(format))
            
        return Content(text)


class Content(ContentBase):
    pass


class Contents:

    def __init__(self, contents=None, guess=False, content_class=Content):
        self.stack = []
        self.set_contents(contents, guess=guess)

    def __iter__(self):
        return iter(self.contents)

    def __len__(self):
        return len(self.contents)

    def __str__(self):
        return '\n'.join([str(c) for c in self])

    def __getitem__(self, index):
        return self.contents[index]

    def end(self):
        self.contents = self.stack.pop()

    def update(self, contents):
        if self.contents:
            self.stack.append(self.contents)
        self.set_contents(contents)

    def __call__(self, name, args=None, kws=None):
        args = args or ()
        kws = kws or {}

        if not hasattr(self.content_class, name):
            raise AttributeError('Unknown attribute "{}"'.format(attr))
            
        contents = []
        for ct in self.contents:
            fn = getattr(ct, name)
            result = fn(*args, **kws)
            contents.append(result)
        self.update(contents)

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

    def combine(self):
        '''
        Distill contents into a single piece of content.
        '''
        if self.contents:
            data = self.data_merge()
            self.update([data])

    def set_contents(self, contents, guess=False):
        self.contents = []
        if contents:
            for content in contents:
                if not isinstance(content, self.content_class):
                    content = self.content_class(content, guess=guess)
                        
                self.contents.append(content)
