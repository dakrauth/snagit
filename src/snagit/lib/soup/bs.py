from bs4 import BeautifulSoup, PageElement, NavigableString, Comment
from bs4 import SoupStrainer  # noqa


def is_soup(what):
    return isinstance(what, BeautifulSoup)


def is_element(what):
    return isinstance(what, PageElement)


def is_navigable_string(what):
    return isinstance(what, NavigableString)


def is_comment(what):
    return isinstance(what, Comment)


def is_empty(el):
    if any(el.attrs):
        return False

    val = el.text or ""
    return not bool(val.strip())
