import re
import sys
from pathlib import Path

import pytest

from snagit import utils
from snagit import repl

from snagit.core import Interpreter, execute_code, execute_script, lexer

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
        self._assert_instruction("foo bar 'baz, spam'", 'foo', ['bar', 'baz, spam'], {})


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
            ['a', 'b2', 12, 'c', 'e34', "f5", 'h'],
            {'g-1': 123, 'i': 'a,b,c', 'j': regex(',"a"')}
        )



def read_test_data(basename):
    return utils.read_file(DATA_DIR / basename)


class TestProgram:

    def test_help(self, capsys):
        text = execute_code('help')
        captured = capsys.readouterr()
        assert 'Commands' in captured.out
        assert not text

        text = execute_code('help help')
        captured = capsys.readouterr()
        assert 'Display help on available commands' in captured.out
        assert not text

        text = execute_code('help ----')
        captured = capsys.readouterr()
        assert 'Unknown command ----' in captured.out
        assert not text

    def test_list(self, capsys):
        interp = Interpreter()
        text = interp.execute('help\nhelp\nhelp')
        captured = capsys.readouterr()

        text = interp.execute('list')
        captured = capsys.readouterr()
        lines = captured.out.splitlines()
        assert len(lines) == 3

    def test_load(self, capsys):
        text = execute_code('load https://example.com')
        assert 'Example Domain' in text

        text = execute_code('load http://$')
        captured = capsys.readouterr()
        assert 'ERROR' in captured.out
        assert '' == text

    def test_load_all(self, capsys):
        text = execute_code('load_all', ['http://httpbin.org/links/2/0', 'http://httpbin.org/links/2/1'])
        assert text == "<html><head><title>Links</title></head><body>0 <a href='/links/2/1'>1</a> </body></html>\n<html><head><title>Links</title></head><body><a href='/links/2/0'>0</a> 1 </body></html>"

    def test_parse_line(self, capsys):
        text = execute_code('parse_line a b "c d" x=9')
        captured = capsys.readouterr().out
        assert "'a', 'b', 'c d'" in captured
        assert "'x': 9" in captured

    def test_print(self, capsys):
        execute_code('print', 'foobar')
        assert 'foobar' == capsys.readouterr().out.strip()

    def test_cache(self):
        interp = Interpreter()
        text = interp.execute('cache')
        assert interp.loader.use_cache == True

    def test_debug(self):
        interp = Interpreter()
        text = interp.execute('debug')
        assert interp.do_debug == True

    def test_end(self):
        contents = 'a b c'.split()
        interp = Interpreter(contents)
        try:
            interp.execute('end')
        except:
            assert False

        interp.execute('merge')
        assert len(interp.contents.stack) == 1
        
        interp.execute('end')
        assert len(interp.contents.stack) == 0

    def test_run(self):
        assert "Hello, world" == execute_code('run tests/script.snagit', 'Hello, world#')

    def test_execute_script(self):
        assert "Hello, world" == execute_script('tests/script.snagit', 'Hello, world#')


class TestRepl:
    
    def test_repl(self, capsys):
        def _inputs():
            yield ''
            yield 'quit'
            yield '?'
            raise KeyboardInterrupt('')

        inputs = _inputs()
        def input_handler(prompt, history=None):
            return next(inputs)

        r = repl.Repl(input_handler=input_handler)
        assert str(r.repl(print_all=True, history=None)) == ''
        
        assert str(r.repl(history=None)) == ''


def test_version():
    from snagit import get_version
    version = [int(i) for i in get_version().split('.')]
    assert len(version) > 1
