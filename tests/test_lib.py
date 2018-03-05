import re
import pytest
from snagit import utils
from snagit.core import execute_code

LINES = [
    'foo bar baz',
    'spam     ',
    'xxxxxxxx',
    'zzzz',
    '        123',
    '   u6ejtryn',
    '456',
]


def join_lines(start=0, end=len(LINES), task=None):
    task = task or (lambda s: s)
    return '\n'.join([task(line) for line in LINES[start:end]])


@pytest.fixture
def lines():
    return join_lines()


class TestLines:
    
    def test_str(self, lines):
        text = execute_code('', lines)
        assert text == lines

    def test_strip(self, lines):
        text = execute_code('strip', lines)
        assert text == join_lines(task=lambda s: s.strip())

    def test_skip_to(self, lines):
        text = execute_code('skip_to 123 keep=False', lines)
        assert text == join_lines(-2)

    def test_read_until(self, lines):
        text = execute_code('read_until 456 keep=False', lines)
        assert text == join_lines(end=-1)

    def test_format(self, lines):
        expected = '\n'.join([
            '{} <{}>'.format(i, line) for i, line in enumerate(LINES, 1)
        ])
        assert expected == execute_code('format "{1} <{0}>"', lines)

    def test_matches(self, lines):
        data = join_lines()
        res = execute_code('matches r"(x|z)+"', data)
        assert res == 'xxxxxxxx\nzzzz'

    def test_merge(self):
        data = [LINES[:], LINES[:]]
        expect = '{}\n{}'.format(join_lines(), join_lines())
        res = execute_code('lines\nmerge', data)
        assert res == expect


class TestText:

    def test_replace_each(self):
        assert 'az bz cz' == execute_code('replace_each z x', 'ax bx cz')

    def test_remove_each(self):
        assert 'a b c' == execute_code('remove_each x z', 'ax bx cz')

    def test_compress_text(self):
        assert 'a\nb c\nd' == execute_code('compress_text', '       a    \n\n\n\n b\t\tc\n\r\nd       ')

    def test_merge(self):
        assert 'a\nb\nc' == execute_code('merge', 'a b c'.split())



def compress(text):
    return ''.join(re.findall(r'([\S]+)', text))


html = '<p>Hello, <b class="foo">world</b></p>'


class TestSoup:

    def setup_method(self):
        utils.set_config(parser='html.parser')

    def test_unwrap(self):
        #import pdb; pdb.set_trace()
        text = execute_code('unwrap b', html)
        assert compress('<p>Hello, world</p>') == compress(text)

        text = execute_code('unwrap p', html)
        assert compress('Hello, <b class="foo">world</b>') == compress(text)

    def test_unwrap_attr(self):
        text = execute_code('unwrap_attr b class', html)
        assert compress('<p>Hello, foo</p>') == compress(text)

    def test_remove_attrs(self):
        h = '<span foo="bar"><b class="b"></b><i class="i" data-foo-bar="#"></i></span>'
        text = execute_code('remove_attrs class', h)
        assert compress('<span foo="bar"><b></b><i data-foo-bar="#"></i></span>') == compress(text)

        text = execute_code('remove_attrs class query=i', h)
        assert compress('<span foo="bar"><b class="b"></b><i data-foo-bar="#"></i></span>') == compress(text)

        text = execute_code('remove_attrs data-* foo', h)
        assert compress('<span><b class="b"></b><i class="i"></i></span>') == compress(text)

    def test_select(self):
        h = '<span foo="bar"><b class="b"></b><i class="i" data-foo-bar="#"></i></span>'
        text = execute_code('select [data-foo-bar]', h)
        assert compress('<i class="i" data-foo-bar="#"></i>') == compress(text)

    def test_replace_tag_string(self):
        text = execute_code('replace_tag_string .foo r"[ld]+" k', html)
        assert compress('<p>Hello, <b class="foo">work</b></p>') == compress(text)

    def test_extract(self):
        text = execute_code('extract .foo', html)
        assert compress('<p>Hello, </p>') == compress(text)


    def test_replace_with(self):
        text = execute_code('replace_with .foo world', html)
        assert compress('<p>Hello, world</p>') == compress(text)

    def test_normalize_tag(self):
        text = execute_code(
            'extract .foo \nnormalize_tag',
            '<p>Hello, <b class="foo">world</b> <i>!</i></p>'
        )
        
        assert compress('<p>Hello,<i>!</i></p>') == compress(text)

    def test_compress(self):
        text = execute_code('select p\nmerge', ['<div><p>Foo</p></div>', '<div><p>Bar</p></div>'])
        assert compress('<p>Foo</p><p>Bar</p>') == compress(text)

    def test_extract_empty(self):
        text = execute_code('extract_empty', '<p>Hello, <i></i>world')
        assert compress('<p>Hello, world</p>') == compress(text)

    def test_find_all(self):
        h = '<span foo="bar"><b class="b"></b><i class="i" data-foo-bar="#"></i></span>'
        text = execute_code('find_all b', h)
        assert compress('<b class="b"></b>') == compress(text)
