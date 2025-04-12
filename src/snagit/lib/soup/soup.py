import re
import logging

from snagit import utils
from snagit.lib import DataProxy
from snagit.core import BaseLibrary
from .formatter import Formatter
from . import bs

logger = logging.getLogger(__name__)
formatter = Formatter(utils.config)


def _struct(elements, *, strip=False):
    results = []
    for el in elements:
        children = el.select("& > *")
        if not children:
            text = el.text.strip() if strip else el.text
            if text:
                results.append(text)
                continue

        inner = [_struct([c], strip=strip) for c in children]
        results.append([val for val in inner if val])

    return results if len(results) > 1 else results[0]


class SoupProxy(DataProxy):
    """
    Handler for manipulating a block of BeautifulSoup.
    """

    def __init__(self, data, strainer=None):
        bs = self.make(data, strainer=strainer)
        self._data = bs

    def __str__(self):
        return formatter(self._data)

    @classmethod
    def merge(cls, all_data):
        results = []
        for soup in all_data:
            results.extend(list(soup))

        return cls(results)

    def struct(self, args, strip=False):
        elements = []
        for arg in args:
            elements.extend(self.select(arg))

        results = _struct(elements, strip=strip)
        return results

    @classmethod
    def make(cls, contents, strainer=None):
        if isinstance(contents, DataProxy):
            if isinstance(contents, SoupProxy):
                return contents._data

            contents = str(contents)

        if isinstance(contents, (str, bytes)):
            return bs.BeautifulSoup(contents, utils.config.parser, parse_only=strainer)

        if not isinstance(contents, list):
            raise ValueError(f"Cannot create soup from type {type(contents)}")  # noqa

        soup = bs.BeautifulSoup("", utils.config.parser)
        soup.contents = contents
        return soup


class Library(BaseLibrary):
    name = "soup"
    data_proxy = SoupProxy

    def soup_strain(self, data, args, kws):
        data = str(data)
        if not data:
            raise ValueError("No html text to strain")

        limit = kws.pop("limit", 0)
        if "class" in kws:
            kws["class_"] = kws.pop("class")
        strainer = bs.SoupStrainer(args[0] if args else None, **kws)
        soup = SoupProxy(data, strainer=strainer)
        if limit:
            soup._data.contents = soup._data.contents[:limit]

        return soup

    def soup_unwrap(self, data, args, kws):
        """
        Replace an element with its child contents.
        """
        # import ipdb; ipdb.set_trace()
        soup = SoupProxy(data)
        args = ",".join(args)
        for el in soup.select(args):
            el.unwrap()
        return soup

    def soup_unwrap_attr(self, data, args, kws):
        """
        Replace an element with the content for a specified attribute.
        """
        soup = SoupProxy(data)
        for el in soup.select(args[0]):
            attrs = getattr(el, "attrs", {})
            what = attrs.get(args[1], "")
            if isinstance(what, (list, tuple)):
                what = " ".join(what)

            el.replace_with(what)

        return soup

    def soup_smooth(self, data, args, kws):
        """
        Combine consecutive navigable strings, compressing whitespace.
        """
        soup = SoupProxy(data)
        args = args or ["*"]
        for arg in args:
            for tag in soup.select(arg):
                tag.smooth()

        return soup

    def soup_extract(self, data, args, kws):
        """
        Removes the specified elements.
        """
        soup = SoupProxy(data)
        args = ",".join(args)
        for el in soup.select(args):
            el.extract()
        return soup

    def soup_replace_content(self, data, args, kws):
        """
        Do replacement on element strings
        """
        soup = SoupProxy(data)
        query, old, new, *other = args
        for el in soup.select(query):
            s = el.string
            if s:
                el.string = utils.replace(s, old, new)

        return soup

    def soup_replace_with(self, data, args, kws):
        """
        Replace tag content.
        """
        soup = SoupProxy(data)
        for el in soup.select(args[0]):
            el.replace_with(args[1])

        return soup

    def soup_find_all(self, data, args, kws):
        """
        Query elements using the `BeautifulSoup.find_all` API.
        """
        soup = SoupProxy(data)
        results = soup.find_all(*args, **kws)
        return results

    def soup_select(self, data, args, kws):
        """
        Query elements matching the CSS selection.
        """
        soup = SoupProxy(data)
        args = args[0] if args else "*"
        results = soup.select(args, limit=kws.get("limit"))
        return results

    def soup_rmempty(self, data, args, kws):
        """
        Remove empty tags
        """
        soup = SoupProxy(data)
        args = ",".join(args or ["*"])
        contents = []
        for node in soup.contents:
            if bs.is_empty(node):
                continue

            elements = node.select(args)
            for el in elements:
                if bs.is_empty(el):
                    el.extract()

            contents.append(node)

        soup.contents = contents
        return soup

    def soup_rmattrs(self, data, args, kws):
        """
        Removes attributes from specified elements.
        """
        soup = SoupProxy(data)
        query = kws.get("query", "*")
        if not args or args[0] == "*":
            attrs_re = re.compile(".+")
        else:
            attrs_re = re.compile(r"({})".format("|".join([a.replace("*", ".*") for a in args])))

        elements = soup.select(query)
        for el in elements:
            el.attrs = {k: v for k, v in el.attrs.items() if not attrs_re.match(k)}

        return soup

    def soup_rmcomments(self, data, args, kws):
        """
        Remove comments from the soup tree or specified args.
        """
        soup = SoupProxy(data)
        args = ",".join(args) if args else "*"
        for el in soup.select(args):
            for comment in el.find_all(string=bs.is_comment):
                comment.decompose()

        return soup
