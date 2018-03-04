import re
import random
import logging
import importlib
from pathlib import Path
from copy import deepcopy
from strutil import is_string, is_regex

logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    warning.warn('Missing `requests` installation', ImportWarning)

try:
    import ipdb as pdb
except ImportError:
    import pdb

GLOBAL_ATTRS = ['class',  'id', 'style']
BAD_ATTRS = [
    'align', 'alink', 'background', 'bgcolor', 'border', 'clear', 'height',
    'hspace', 'language', 'link', 'nowrap', 'start', 'text', 'type', 'vlink',
    'vspace', 'width'
]

BAD_TAGS = {
    'applet': None,
    'basefont': None,
    'center': 'span',
    'dir': 'ul',
    'embed': 'object',
    'font': 'span',
    'isindex': None,
    'listing': 'pre',
    'marquee': 'p',
    'menu': 'ul',
    'plaintext': 'pre',
    's': 'span',
    'strike': 'span',
    'tt': 'code',
    'u': 'span',
    'xmp': 'pre',
}

DEFAULT_CONFIG = {
    'range_delimiter': '{}',
    'user_agents': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:11.0) Gecko/20100101 Firefox/11.0',  # noqa
        'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:22.0) Gecko/20100 101 Firefox/22.0',  # noqa
        'Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_4) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.46 Safari/536.5',  # noqa
        'Mozilla/5.0 (Windows; Windows NT 6.1) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.46 Safari/536.5',  # noqa
    ),
    'bad_tags': BAD_TAGS,
    'bad_attrs': BAD_ATTRS,
    'non_closing_tags': 'hr br link meta img base input param source'.split(),
    'no_indent_tags': 'body head tr'.split(),
    'parser': 'html.parser'
}

_config_settings = deepcopy(DEFAULT_CONFIG)


def import_string(what):
    mod_name, name = what.rsplit('.', 1)
    mod = importlib.import_module(mod_name)
    return getattr(mod, name)


def normalize_search_attrs(attrs):
    if attrs in (None, '*'):
        return re.compile('.+')

    return re.compile(
        r'({})'.format('|'.join([a.replace('*', '.*') for a in attrs]))
    )


def set_config(**kws):
    global _config_settings
    new_config = deepcopy(_config_settings)
    new_config.update(kws)
    _config_settings = new_config
    return new_config


def get_config(key=None, default=None):
    return _config_settings.get(key, default) if key else _config_settings


def read_url(url):
    '''
    Read data from ``url``.

    Returns a 2-tuple of (text, content_type)
    '''
    ua = get_config('user_agents')
    headers = {'accept-language': 'en-US,en'}
    if ua:
        headers['User-Agent'] = random.choice(ua)

    r = requests.get(url, headers=headers)
    if not r.ok:
        raise requests.HTTPError('URL {}: {}'.format(r.reason, url))

    ct = r.headers.get('content-type')
    return (r.text, ct)


def absolute_filename(filename):
    '''
    Do all those annoying things to arrive at a real absolute path.
    '''
    return str(Path(filename).expanduser().resolve())


def write_file(filename, data, mode='w', encoding='utf8'):
    '''
    Write ``data`` to properly encoded file.
    '''
    filename = absolute_filename(filename)
    with open(filename, mode, encoding=encoding) as fp:
        fp.write(data)


def read_file(filename, encoding='utf8'):
    '''
    Read ``data`` from properly encoded file.
    '''
    filename = absolute_filename(filename)
    with open(filename, 'r', encoding=encoding) as fp:
        return fp.read()


range_re = re.compile(r'''([a-zA-Z]-[a-zA-Z]|\d+-\d+)''', re.VERBOSE)


def _get_range_run(start, end):
    if start.isdigit():
        fmt = '{}'
        if len(start) > 1 and start[0] == '0':
            fmt = '{{:0>{}}}'.format(len(start))
        return [fmt.format(c) for c in range(int(start), int(end) + 1)]

    return [chr(c) for c in range(ord(start), ord(end) + 1)]


def get_range_set(text):
    '''
    Convert a string of range-like tokens into list of characters.

    For instance, ``'A-Z'`` becomes ``['A', 'B', ..., 'Z']``.
    '''
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
        start, end = m.group().split('-')
        values.extend(_get_range_run(start, end))

    return values


def expand_range_set(sources, range_set=None):
    if is_string(sources):
        sources = [sources]

    if not range_set:
        return sources

    results = []
    chars = get_range_set(range_set)
    delim = get_config('range_delimiter')
    for src in sources:
        results.extend([src.replace(delim, c) for c in chars])

    return results


def escaped(txt):
    for cin, cout in (('\\n', '\n'), ('\\t', '\t')):
        txt = txt.replace(cin, cout)

    return txt
