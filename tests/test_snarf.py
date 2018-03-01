import re
import sys
from pathlib import Path

import pytest

from snarf import utils
from snarf.core import Interpreter, execute_code, lexer

HERE = Path(__file__).parent
DATA_DIR = HERE / 'data'
regex = re.compile

class TestParse:

    def _assert_instruction(self, line, expect_cmd, expect_args=None, expect_kws=None):
        expect_args = expect_args or ()
        expect_kws = expect_kws or {}
        inst = next(lexer(line))

        assert inst.cmd == expect_cmd
        assert len(inst.args) == len(expect_args)
        for actual, expect in zip(inst.args, expect_args):
            if utils.is_regex(expect):
                assert expect.pattern == actual.pattern
            else:
                assert actual == expect
            
        assert inst.kws == expect_kws
    
    def test_single_quote(self):
        self._assert_instruction("foo, bar 'baz spam'", 'foo', ['bar', 'baz, spam'], {})


    def test_regex(self):
        self._assert_instruction("x r'[abc]'", 'x', [regex('[abc]')], {})


    def test_arg_kwarg_quote(self):
        self._assert_instruction("z foo=bar baz 'foo'", 'z', ['baz', 'foo'], {'foo': 'bar'})


    def test_regex_arg_regex_kws(self):
        self._assert_instruction(
            """replace r'a+b' x='a b c' y=23 z=True baz=r'spam+'""",
            'replace',
            [regex('a+b')],
            {'x': 'a b c', 'y': 23, 'z': True, 'baz': regex('spam+')}
        )


    def test_underscores(self):
        self._assert_instruction(
            """commandx _=34 __=None""",
            'commandx',
            (),
            {'_': 34, '__': None}
        )
        
        self._assert_instruction(
            """command abc7 'True' _ _=34 __=None""",
            'command',
            ['abc7', 'True', '_'],
            {'_': 34, '__': None}
        )

    def test_complex(self):
        self._assert_instruction(
            """CMD a b2,  12 'c'  e34, "f5" g-1=123,h,i="a,b,c" j=r',"a"' """,
            'cmd',
            ['a', 'b2', 12, "'c'", 'e34', "f5", 'h'],
            {'g-1': 123, 'i': 'a,b,c', 'j': regex(',"a"')}
        )


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


def read_test_data(basename):
    return utils.read_file(DATA_DIR / basename)


class TestProgram:

    def test_help(self, capsys):
        text = execute_code('help')
        captured = capsys.readouterr()
        assert 'Commands' in captured.out
        assert not text

    def test_list(self, capsys):
        interp = Interpreter()
        text = interp.execute('help\nhelp\nhelp')
        captured = capsys.readouterr()

        text = interp.execute('list')
        captured = capsys.readouterr()
        assert len(captured.out.splitlines()) == 4

    def test_load(self, capsys):
        text = execute_code('load https://example.com')
        assert 'Example Domain' in text


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

    def _xyztest_end(self, lines):
        text = lines('skip_to zzzz')
        lines.end()
        text = str(lines)
        assert text == join_lines()
