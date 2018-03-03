'''
Test snarf.utils
'''
import re
import json
import string

import pytest
from snarf import utils


def test_import_string():
    make_lines = utils.import_string('snarf.lib.lines.make_lines')
    assert make_lines.kind == 'Lines'


def test_normalize_search_attrs():
    assert utils.normalize_search_attrs('*') == re.compile(r'.+')
    assert utils.normalize_search_attrs('a b c'.split()) == re.compile(r'(a|b|c)')


def test_get_range_set():
    assert utils.get_range_set('ace') == list('ace')
    assert utils.get_range_set('A-Z') == list(string.ascii_uppercase)
    assert utils.get_range_set('3-7') == list('34567')
    assert utils.get_range_set('a0-3x') == list('a0123x')
    assert utils.get_range_set('ac-f') == list('acdef')


def test_expand_range_set():
    assert utils.expand_range_set('/foo/bar/a.txt') == ['/foo/bar/a.txt']
    assert utils.expand_range_set('/foo/bar/{}.txt', 'a-c') == [
        '/foo/bar/a.txt', '/foo/bar/b.txt', '/foo/bar/c.txt'
    ]


def test_read_url():
    data, ct = utils.read_url('http://httpbin.org/get')
    data = json.loads(data)
    assert 'headers' in data
    assert ct == 'application/json'


def test_read_file():
    text = utils.read_file('../snarf/tests/test_utils.py')
    assert text.startswith("'''\nTest snarf.utils")


def test_set_config():
    utils.set_config(bad_tags='bad_tags')
    assert utils.get_config('bad_tags') == 'bad_tags'
