import re
import sys
from pathlib import Path

from snarf import script
from snarf import utils
from snarf.core import Contents, make_html

HERE = Path(__file__).parent
DATA_DIR = HERE / 'data'


def read_test_data(basename):
    return utils.read_file(DATA_DIR / basename))


def test_simple():
    data = read_test_data('lines.txt')
    lines = Contents([data])

    lines.strip()
    text = str(lines)
    assert text == '''foo bar baz\nspam\nxxxxxxxx\nzzzz\n123\nu6ejtryn\n456'''

    lines.skip_to('123', False)
    text = str(lines)
    assert text == 'u6ejtryn\n456'

    lines.read_until('456', False)
    text = str(lines)
    assert text == 'u6ejtryn'

    lines.end()
    text = str(lines)
    assert text == 'u6ejtryn\n456'


def _do_instruction(line, expect_cmd, expect_args=None, expect_kws=None):
    expect_args = expect_args or ()
    expect_kws = expect_kws or {}
    prog = script.Script(line)
    inst = prog.instructions[0]

    assert inst.cmd == expect_cmd
    assert len(inst.args) == len(expect_args)
    for actual, expect in zip(inst.args, expect_args):
        if utils.is_regex(expect):
            assert expect.pattern == actual.pattern
        else:
            assert actual == expect
        
    assert inst.kws == expect_kws


def test_parse_instruction():
    _do_instruction("foo bar 'baz spam'", 'foo', ['bar', 'baz spam'], {})
    _do_instruction("x r'[abc]'", 'x', [regex('[abc]')], {})
    _do_instruction("z foo=bar baz 'foo'", 'z', ['baz', 'foo'], {'foo': 'bar'})
    
    _do_instruction(
        """replace r'a+b' x='a b c' y=23 z=True baz=r'spam+'""",
        'replace',
        [regex('a+b')],
        {'x': 'a b c', 'y': 23, 'z': True, 'baz': regex('spam+')}
    )

    _do_instruction(
        """commandx _=34 __=None""",
        'commandx',
        expect_kws={'_': 34, '__': None}
    )
    
    _do_instruction(
        """command abc7 'True' _ _=34 __=None""",
        'command',
        ['abc7', 'True', '_'],
        {'_': 34, '__': None}
    )


def test_select_attr():
    bs = make_html(read_test_data('httpbin_links.html'))
    h = Contents([bs])
    h.select_attr('a', 'href')
    lines = h.data_merge()
    assert lines == ['/links/10/{}'.format(i) for i in range(1,10)]


def test_dumps():
    bs = make_html(read_test_data('httpbin_links.html'))
    h = Contents([bs])
    text = str(h)
    assert text == read_test_data('expected_httpbin_links.html')

