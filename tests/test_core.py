import re
from pathlib import Path

from snagit import __version__
from snagit import utils

from snagit.core import Parser

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
regex = re.compile


def _assert_instruction(line, expect_cmd, expect_args=None, expect_kws=None):
    expect_args = expect_args or ()
    expect_kws = expect_kws or {}
    inst = next(Parser().process(line))

    assert inst.cmd == expect_cmd
    assert len(inst.args) == len(expect_args)
    for actual, expect in zip(inst.args, expect_args):
        if utils.is_regex(expect):
            assert expect.pattern == actual.pattern
        else:
            assert actual == expect

    assert inst.kwargs == expect_kws


def test_single_quote():
    _assert_instruction("foo bar 'baz, spam'", "foo", ["bar", "baz, spam"], {})


def test_regex():
    _assert_instruction("x /[abc]/", "x", [regex("[abc]")], {})


def test_arg_kwarg_quote():
    _assert_instruction("z foo=bar baz 'foo'", "z", ["baz", "foo"], {"foo": "bar"})


def test_regex_arg_regex_kws():
    _assert_instruction(
        """replace /a+b/ x='a b c' y=23 z=True baz=/spam+/""",
        "replace",
        [regex("a+b")],
        {"x": "a b c", "y": 23, "z": True, "baz": regex("spam+")},
    )


def test_underscores():
    _assert_instruction("""commandx _=34 __=None""", "commandx", (), {"_": 34, "__": None})

    _assert_instruction(
        """command abc7 True _ _=34 __=None""",
        "command",
        ["abc7", True, "_"],
        {"_": 34, "__": None},
    )


def test_complex():
    _assert_instruction(
        """CMD a b2,  12 'c'  e34, "f5" g_1=123,h,i="a,b,c" j=/,"a"/ """,
        "cmd",
        ["a", "b2,", 12, "c", "e34,", "f5"],
        {"g_1": "123,h,i=a,b,c", "j": regex(',a')},
    )


def test_version():
    version = [int(i) for i in __version__.split(".")]
    assert len(version) > 1
