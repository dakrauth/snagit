import re
import types
import logging
from pathlib import Path

from cachely.client import Client

logger = logging.getLogger(__name__)
ReType = type(re.compile(""))


try:
    import ipdb as pdb
except ImportError:
    import pdb

try:
    import lxml
except ImportError:
    lxml = None

GLOBAL_ATTRS = ["class", "id", "style"]
BAD_ATTRS = [
    "align",
    "alink",
    "background",
    "bgcolor",
    "border",
    "clear",
    "height",
    "hspace",
    "language",
    "link",
    "nowrap",
    "start",
    "text",
    "type",
    "vlink",
    "vspace",
    "width",
]

BAD_TAGS = {
    "applet": None,
    "basefont": None,
    "center": "span",
    "dir": "ul",
    "embed": "object",
    "font": "span",
    "isindex": None,
    "listing": "pre",
    "marquee": "p",
    "menu": "ul",
    "plaintext": "pre",
    "s": "span",
    "strike": "span",
    "tt": "code",
    "u": "span",
    "xmp": "pre",
}

range_re = re.compile(r"""([a-zA-Z]-[a-zA-Z]|\d+-\d+)""", re.VERBOSE)
set_trace = pdb.set_trace
post_mortem = pdb.post_mortem
config = types.SimpleNamespace(
    **{
        "range_delimiter": "{}",
        "bad_tags": BAD_TAGS,
        "bad_attrs": BAD_ATTRS,
        "non_closing_tags": "hr br link meta img base input param source".split(),
        "no_indent_tags": "body head tbody tfoot caption".split(),
        "parser": "lxml" if lxml else "html.parser",
    }
)


class Loader(Client):
    def __init__(self, *args, **kwargs):
        self.use_cache = kwargs.pop("use_cache", False)

    def read_url(self, url):
        if url.lower().startswith("file://"):
            url = url[7:]

        if "://" not in url:
            return Path(url).read_text()

        return super().read_url(url)

    def load_source(self, url, use_cache=None):
        use_cache = self.use_cache if use_cache is None else bool(use_cache)
        if use_cache:
            return super().load_source(url)

        return self.read_url(url)

    def load_sources(self, urls, use_cache=None):
        return [self.load_source(src, use_cache=use_cache) for src in urls]


def _get_range_run(start, end):
    if start.isdigit():
        fmt = "{}"
        if len(start) > 1 and start[0] == "0":
            fmt = "{{:0>{}}}".format(len(start))
        return [fmt.format(c) for c in range(int(start), int(end) + 1)]

    return [chr(c) for c in range(ord(start), ord(end) + 1)]


def get_range_set(text):
    """
    Convert a string of range-like tokens into list of characters.

    For instance, ``'A-Z'`` becomes ``['A', 'B', ..., 'Z']``.
    """
    values = []
    while text:
        m = range_re.search(text)
        if not m:
            if text:
                values.extend(list(text))
            break

        i, j = m.span()
        if i:
            values.extend(list(text[:i]))

        text = text[j:]
        start, end = m.group().split("-")
        values.extend(_get_range_run(start, end))

    return values


def expand_range_set(sources, range_set=None):
    if is_string(sources):
        sources = [sources]

    if not range_set:
        return sources

    results = []
    chars = get_range_set(range_set)
    delim = config.range_delimiter
    for src in sources:
        results.extend([src.replace(delim, c) for c in chars])

    return results


def escaped(txt):
    for cin, cout in (("\\n", "\n"), ("\\t", "\t")):
        txt = txt.replace(cin, cout)

    return txt


def is_string(obj):
    """
    Check if ``obj`` is a string
    """
    return isinstance(obj, str)


def is_regex(obj):
    """
    Check if ``obj`` is a regular expression

    """
    return isinstance(obj, ReType)


def replace(text, old, new, count=None, strip=False):
    """
    Replace an ``old`` subset of ``text`` with ``new``.

    ``old`` type may be either a string or regular expression.

    If ``strip``, remove all leading/trailing whitespace.

    If ``count``, replace the specified number of occurence, otherwise replace all.
    """
    if is_string(old):
        text = text.replace(old, new, -1 if count is None else count)
    else:
        text = old.sub(new, text, 0 if count is None else count)

    if strip:
        text = text.strip(None if strip is True else strip)

    return text


def remove(text, what, count=None, strip=False):
    """
    Like ``replace``, where ``new`` replacement is an empty string.
    """
    return replace(text, what, "", count=count, strip=strip)


def replace_each(text, items, count=None, strip=False):
    """
    Like ``replace``, where each occurrence in ``items`` is a 2-tuple of
    ``(old, new)`` pair.
    """
    for a, b in items:
        text = replace(text, a, b, count=count, strip=strip)
    return text


def remove_each(text, items, count=None, strip=False):
    """
    Like ``remove``, where each occurrence in ``items`` is ``what`` to remove.
    """
    for item in items:
        text = remove(text, item, count=count, strip=strip)
    return text


# TODO: not sure if ``contains`` is appropriate, maybe ``matches``?
def matches(text, what):
    """
    Check if ``what`` occurs in ``text``

    """
    return text.find(what) > -1 if is_string(what) else what.match(text)


contains = matches


def find_first(data, what):
    """
    Search for ``what`` in the iterable ``data`` and return the index of the
    first match. Return ``None`` if no match found.
    """
    for i, line in enumerate(data):
        if contains(line, what):
            return i

    return None


def splitter(text, token=None, expected=2, default="", strip=False):
    """
    Split ``text`` by ``token`` into at least ``expected`` number of results.

    When ``token`` is ``None``, the default for Python ``str.split`` is used,
    which will split on all whitespace.

    ``token`` may also be a regex.

    If actual number of results is less than ``expected``, pad with ``default``.

    If ``strip``, than do just that to each result.
    """
    if is_string(token) or token is None:
        bits = text.split(token, expected - 1)
    else:
        bits = [s for s in token.split(text, expected) if s]

    if strip:
        bits = [s.strip() for s in bits]

    n = len(bits)
    while n < expected:
        bits.append(default)
        n += 1

    return bits
