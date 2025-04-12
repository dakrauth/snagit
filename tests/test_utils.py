"""
Test snagit.utils
"""

import re
import string

from snagit import utils


def test_get_range_set():
    assert utils.get_range_set("ace") == list("ace")
    assert utils.get_range_set("A-Z") == list(string.ascii_uppercase)
    assert utils.get_range_set("3-7") == list("34567")
    assert utils.get_range_set("001-003") == ["001", "002", "003"]
    assert utils.get_range_set("a0-3x") == list("a0123x")
    assert utils.get_range_set("ac-f") == list("acdef")


def test_expand_range_set():
    assert utils.expand_range_set("/foo/bar/a.txt") == ["/foo/bar/a.txt"]
    assert utils.expand_range_set("/foo/bar/{}.txt", "a-c") == [
        "/foo/bar/a.txt",
        "/foo/bar/b.txt",
        "/foo/bar/c.txt",
    ]


def test_replace_1():
    assert "is expected" == utils.replace("  not expected \t \n", "not", "is", strip=True)


def test_replace_re1():
    assert "here are random numbers" == utils.replace(
        "here are 123 random 456 numbers", re.compile(r"\s+\d+\s+"), " "
    )


def test_splitter_1():
    assert ["Hello, world", "", "", ""] == utils.splitter("Hello, world", token="@", expected=4)


def test_splitter_2():
    assert ["Hello,", "world", ""] == utils.splitter("Hello, world", expected=3)


def test_splitter_3():
    assert ["1", "2", "0"] == utils.splitter(
        "X 1 Y 2", re.compile(r" ?[A-Z] ?"), expected=3, default="0"
    )


def test_find_first_1():
    items = "abc 123 ------ spam eggs".split()
    assert utils.find_first(items, "-") == 2
    assert utils.find_first(items, re.compile(r"\d+")) == 1
    assert utils.find_first(items, "X") is None


def test_replace_each_1():
    result = utils.replace_each(
        "line 1\nline 2\nline 3", (("line", "Line"), (re.compile(r"(\d+)"), r"#\1"))
    )
    assert result == "Line #1\nLine #2\nLine #3"
