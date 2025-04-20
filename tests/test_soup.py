import re
from snagit.core import execute_code
from snagit.lib.soup import bs
from snagit.lib.soup.formatter import Formatter
from snagit.utils import config

HTML = '<p>Hello, <b class="foo">world</b></p>'
HTML2 = """<div>
    Hello, world <!-- silly comment -->
    <div class="foo"><p>!<!-- spam eggs and spam --></p></div>
</div>"""
HTML3 = """
    
"""

def compress(text):
    text = re.sub(r"\n\s+", " ", text)
    text = re.sub(r"\s\s+", " ", text)
    return "".join(re.findall(r"([\S]+)", text))


def almost(text):
    return text.replace("\n", "")


def assert_html_equal(expect, actual):
    expect = compress(expect)
    actual = compress(actual)
    assert expect == actual


def test_strain():
    text = execute_code("strain p", HTML)
    assert_html_equal(HTML, text)

    text = execute_code("strain class=foo", HTML)
    assert_html_equal('<b class="foo">world</b>', text)


def test_rmcomments():
    text = execute_code("strain div\nrmcomments", HTML2)
    assert_html_equal('<div>Hello, world<div class="foo"><p>!</p></div></div>', text)

    text = execute_code("strain div\nrmcomments .foo", HTML2)
    assert_html_equal(
        '<div>Hello, world <!-- silly comment --><div class="foo"><p>!</p></div></div>', text
    )


def test_unwrap():
    text = execute_code("strain p\nunwrap b", HTML)
    assert_html_equal("<p>Hello, world</p>", text)

    text = execute_code("strain p\nunwrap p", HTML)
    assert_html_equal('Hello, <b class="foo">world</b>', text)


def test_unwrap_attr():
    text = execute_code("strain p\nunwrap b attr=class", HTML)
    assert_html_equal("<p>Hello, foo</p>", text)


def test_rmattrs():
    h = '<span foo="bar"><b class="b"></b><i class="i" data-foo-bar="#"></i></span>'
    text = execute_code("strain span\nrmattrs class", h)
    assert_html_equal('<span foo="bar"><b></b><i data-foo-bar="#"></i></span>', text)

    text = execute_code("strain span\nrmattrs class query=i", h)
    assert_html_equal('<span foo="bar"><b class="b"></b><i data-foo-bar="#"></i></span>', text)

    text = execute_code("strain span\nrmattrs data-* foo", h)
    assert_html_equal('<span><b class="b"></b><i class="i"></i></span>', text)


def test_select():
    h = '<span foo="bar"><b class="b"></b><i class="i" data-foo-bar="#"></i><b>x</b></span>'
    result = execute_code("select [data-foo-bar]", h)
    assert '<i class="i" data-foo-bar="#"></i>' == almost(result)

    result = execute_code("select b", h)
    assert '<b class="b"></b><b>x</b>' == almost(result)

def test_replace_content():
    text = execute_code('strain p\nreplace_content .foo /[ld]+/ k', HTML)
    assert_html_equal('<p>Hello, <b class="foo">work</b></p>', text)


def test_extract():
    text = execute_code("strain p\nextract .foo", HTML)
    assert_html_equal("<p>Hello, </p>", text)


def test_replace_with():
    text = execute_code("strain p\nreplace_with .foo world", HTML)
    assert_html_equal("<p>Hello, world</p>", text)


def test_smooth():
    text = execute_code(
        "strain p\nextract .foo \nsmooth", '<p>Hello, <b class="foo">world</b> <i>!</i></p>'
    )
    assert_html_equal("<p>Hello,<i>!</i></p>", text)


def test_merge():
    text = execute_code("strain p\nmerge", ["<div><p>Foo</p></div>", "<div><p>Bar</p></div>"])
    assert_html_equal("<p>Foo</p><p>Bar</p>", text)


def test_rmempty():
    text = execute_code("strain p\nrmempty", "<p>Hello, <i></i>world")
    assert_html_equal("<p>Hello, world</p>", text)


def test_find_all():
    b = '<b class="b"></b>'
    h = f'<span foo="bar">{b}<i class="i" data-foo-bar="#"></i></span>'
    text = execute_code("find_all b", h)
    assert f"{b}" == text

    h = f'{h}{b}'
    text = execute_code("find_all b", h)
    assert f"{b}{b}" == almost(text)


def test_bs(BS):
    soup = BS(HTML, "html.parser")
    assert bs.is_soup(soup)

    assert bs.is_element(soup.p)
    assert bs.is_empty(soup.p.b) is False


def test_formatter(BS):
    formatter = Formatter(config)
    soup = BS(HTML, "html.parser")
    assert formatter(soup) == formatter(soup.contents)
    assert formatter(bs.BeautifulSoup("", "html.parser")) == ""

    soup = BS("""<!DOCTYPE html><html><body><br/></body></html>""", "html.parser")
    assert formatter(soup, doctype=True) == "\n".join([
        "<!doctype html>",
        "<html>",
        "<body>",
        "    <br>",
        "</body>",
        "</html>",
    ])

