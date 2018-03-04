# -*- coding:utf8 -*-
import re
import os
import json
import logging
from copy import copy
from pprint import pformat

import bs4
import strutil

from . import DataProxy, library
from .. import utils

logger = logging.getLogger(__name__)
register = library.register('Soup')
_feature = None


def get_bs4_feature():
    global _feature
    if _feature is None:
        _feature = utils.get_config('parser')

    return _feature


class Formatter:

    def __init__(self):
        self.non_closing = utils.get_config('non_closing_tags')
        self.no_indent = utils.get_config('no_indent_tags')

    def get_attrs(self, el):
        orig = getattr(el, 'attrs', {}) or {}
        return {
            k: ' '.join(v) if isinstance(v, (list, tuple)) else v
            for k, v in orig.items()
        }

    def format_attrs(self, el):
        attrs = ''
        orig = getattr(el, 'attrs', {}) or {}
        if orig:
            for key, vals in orig.items():
                vals = ' '.join(vals) if isinstance(vals, (list, tuple)) else vals  # noqa
                attrs += ' {}="{}"'.format(key, vals)

        return attrs

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
                lines.append(
                    '{}{}</{}>'.format(line, el.contents[0].strip(), el.name)
                )
        else:
            lines.append('{}</{}>'.format(line, el.name))

        return lines

    def format(self, el, depth=0, prefix='    ', doctype=True):
        lines = []
        if not el and el.contents:
            return ''

        contents = iter(el.contents)
        if isinstance(el, bs4.BeautifulSoup):
            if not el.contents:
                return ''

            first = el.contents[0]
            if isinstance(first, bs4.Doctype):
                lines.append(str(first.output_ready()).strip())
                next(contents)

        for child in contents:
            lines = self.format_element(child, lines, depth, prefix)

        # from pprint import pprint; pprint(lines)
        return '\n'.join(lines)


formatter = Formatter().format


def is_soup(what):
    return isinstance(what, bs4.BeautifulSoup)


def is_element(what):
    return isinstance(what, bs4.PageElement)


def is_navigable_string(what):
    return isinstance(what, bs4.NavigableString)


def make_soup(contents='', feature=None):
    feature = feature or get_bs4_feature()
    if isinstance(contents, (str, bytes)):
        return bs4.BeautifulSoup(contents, feature)

    if is_soup(contents):
        contents = contents.contents

    if is_element(contents):
        contents = [contents]
    elif not isinstance(contents, list):
        raise ValueError('Cannot create soup from type {}'.format(type(contents)))  # noqa

    soup = bs4.BeautifulSoup('', feature)
    for el in contents:
        soup.append(copy(el))

    return soup


class Soup(DataProxy):
    '''
    Handler for manipulating a block of Soup.
    '''

    def __init__(self, data):
        if isinstance(data, Soup):
            data = data._data

        self._data = make_soup(data if is_soup(data) else str(data))

    def __str__(self):
        return formatter(self._data)

    @classmethod
    def merge(cls, all_data):
        results = []
        for soup in all_data:
            results += [copy(e) for e in soup.children]

        return cls(make_soup(results))


bad_attrs = utils.get_config('bad_attrs')


def _invoke_cmd(data, cmd, args):
    soup = Soup(data)
    for item in args:
        for el in soup.select(item):
            method = getattr(el, cmd)
            method()

    return soup


@register
def unwrap(data, args, kws):
    '''
    Replace an element with its child contents.
    '''
    return _invoke_cmd(data, 'unwrap', args)


@register
def unwrap_attr(data, args, kws):
    '''
    Replace an element with the content for a specified attribute.
    '''
    soup = Soup(data)
    for el in soup.select(args[0]):
        what = getattr(el, 'attrs', {}).get(args[1], '')
        if isinstance(what, (list, tuple)):
            what = ' '.join(what)
        
        el.replace_with(what)

    return soup


@register
def normalize_tag(data, args, kws):
    '''
    Combine consecutive navigable strings, compressing whitespace.
    '''
    args = args or ['*']
    soup = Soup(data)
    for arg in args:
        for tag in soup.select(arg):
            cleaned = []
            children = []
            while tag.contents:
                children.append(tag.contents[0].extract())

            for el in children:
                if isinstance(el, bs4.NavigableString):
                    result = ' '.join(el.split())
                    cleaned.append(result)
                else:
                    if cleaned:
                        tag.append(' '.join(cleaned))

                    tag.append(el)
                    cleaned = []

            if cleaned:
                tag.append(' '.join(cleaned))

    return soup


@register
def extract(data, args, kws):
    '''
    Removes the specified elements.
    '''
    return _invoke_cmd(data, 'extract', args)


@register
def replace_tag_string(data, args, kws):
    '''
    Do replacement on element strings
    '''
    query, old, new, *other = args
    soup = Soup(data)
    for el in soup.select(query):
        s = el.string
        if s:
            el.string = strutil.replace(s, old, new)

    return soup


@register
def replace_with(data, args, kws):
    '''
    Replace the specified tag with some plain text.
    '''
    soup = Soup(data)
    for el in soup.select(args[0]):
        el.replace_with(args[1])

    return soup


def _handle_results(soup, results):
    logger.debug('Selected {} matches'.format(len(results)))
    if results:
        soup._data = make_soup(results)

    return soup


@register
def find_all(data, args, kws):
    '''
    Query elements using the `BeautifulSoup.find_all` API.
    '''
    soup = Soup(data)
    results = soup.find_all(*args, **kws)
    return _handle_results(soup, results)


@register
def select(data, args, kws):
    '''
    Query elements matching the CSS selection.
    '''
    soup = Soup(data)
    args = args[0] if args else '*'
    results = soup.select(args, limit=kws.get('limit'))
    return _handle_results(soup, results)


@register
def extract_empty(data, args, kws):
    '''
    Remove empty tags
    '''
    soup = Soup(data)
    args = args or ['*']
    for arg in args:
        for el in soup.select(arg):
            if not (any(el.attrs) or any(el.stripped_strings)):
                el.extract()

    return soup


@register
def remove_attrs(data, args, kws):
    '''
    Removes the specified attributes from all elements.
    '''
    query = kws.get('query', '*')
    attrs_re = utils.normalize_search_attrs(args)
    soup = Soup(data)

    elements = soup.select(query)
    for el in elements:
        el.attrs = {
            k: v for k, v in el.attrs.items()
            if not attrs_re.match(k)
        }

    return soup
