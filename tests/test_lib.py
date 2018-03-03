import pytest
from snarf.core import execute_code

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


