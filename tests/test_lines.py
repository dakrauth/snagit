import pytest
from snagit.core import execute_code

LINES = [
    "foo bar baz",
    "spam     ",
    "xxxxxxxx",
    "zzzz",
    "        123",
    "   u6ejtryn",
    "456",
]


def join_lines(start=0, end=len(LINES), task=None):
    task = task or (lambda s: s)
    return "\n".join([task(line) for line in LINES[start:end]])


@pytest.fixture
def lines():
    return join_lines()


def test_str(lines):
    text = execute_code("", lines)
    assert text == lines


def test_strip(lines):
    text = execute_code("strip", lines)
    assert text == join_lines(task=lambda s: s.strip())


def test_skip_to(lines):
    text = execute_code("skip_to 123 keep=False", lines)
    assert text == join_lines(-2)


def test_read_until(lines):
    text = execute_code("read_until 456 keep=False", lines)
    assert text == join_lines(end=-1)


def test_format(lines):
    expected = "\n".join([f"{i} <{line}>" for i, line in enumerate(LINES, 1)])
    assert expected == execute_code('format "{1} <{0}>"', lines)


def test_matches(lines):
    data = join_lines()
    res = execute_code('matches r"(x|z)+"', data)
    assert res == "xxxxxxxx\nzzzz"


def test_merge(lines):
    data = [LINES[:], LINES[:]]
    expect = f"{lines}\n{lines}"
    res = execute_code("lines\nmerge", data)
    assert res == expect
