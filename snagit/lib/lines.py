# -*- coding:utf8 -*-
import re
import os
import logging
from pprint import pformat

import strutil
from . import DataProxy, library

logger = logging.getLogger(__name__)
register = library.register('Lines')


def is_lines(what):
    return isinstance(what, (list, tuple))


def _prepare_lines(data):
    if is_lines(data):
        return list(data)
    elif isinstance(data, Lines):
        return data._data[:]

    return str(data).splitlines()


class Lines(DataProxy):
    '''
    Handler class for manipulating and traversing lines of text.
    '''

    def __init__(self, data):
        super().__init__(_prepare_lines(data))

    def __str__(self):
        return '\n'.join(self._data)

    @classmethod
    def merge(cls, all_data):
        data = []
        for lines in all_data:
            data += lines._data

        return cls(data)


@register
def format(data, args, kws):
    '''
    Format each line, where the current line is passed using {}.
    '''
    fmt = args[0]
    return Lines([
        fmt.format(line, lineno)
        for lineno, line in enumerate(_prepare_lines(data), 1)
    ])


@register
def strip(data, args, kws):
    '''
    Strip whitespace from content.
    '''
    return Lines([l.strip() for l in _prepare_lines(data)])


@register
def lines(data, args, kws):
    return Lines(_prepare_lines(data))


@register
def skip_to(data, args, kws):
    '''
    Skip lines until finding a matching line.
    '''
    lines = _prepare_lines(data)
    keep = kws.pop('keep', False)
    found = strutil.find_first(lines, str(args[0]))
    if found is not None:
        if not keep:
            found += 1

        lines = lines[found:]

    return Lines(lines)


@register
def read_until(data, args, kws):
    '''
    Save lines until finding a matching line.
    '''
    keep = kws.pop('keep', False)
    lines = _prepare_lines(data)
    found = strutil.find_first(lines, str(args[0]))
    if found is not None:
        if keep:
            found += 1

        lines = lines[:found]

    return Lines(lines)


@register
def matches(data, args, kws):
    '''
    Save lines matching the input.
    '''
    return Lines(
        [l for l in _prepare_lines(data) if strutil.matches(l, args[0])]
    )
