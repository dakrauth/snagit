import re
import os
import codecs
import random
import logging
import mimetypes
import itertools
from strutil import is_string, is_regex

try:
    import requests
except ImportError:
    warning.warn('Missing `requests` installation', ImportWarning)
    
try:
    import ipdb as pdb
except ImportError:
    import pdb

DEFAULT_DELIMITER = '@@@'
USER_AGENTS = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:11.0) Gecko/20100101 Firefox/11.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:22.0) Gecko/20100 101 Firefox/22.0',
    'Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_4) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.46 Safari/536.5',
    'Mozilla/5.0 (Windows; Windows NT 6.1) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.46 Safari/536.5',
)

logger = logging.getLogger('snarf')
logger.addHandler(logging.NullHandler())

#-------------------------------------------------------------------------------
def guess_extension(content_type):
    if ';' in content_type:
        content_type = content_type.split(';')[0]
    
    ext = mimetypes.guess_extension(content_type, False)
    if not ext:
        content_type = content_type.replace('/x-', '/')
        ext = mimetypes.guess_extension(content_type, False)
    
    return ext or ''


#---------------------------------------------------------------------------
def read_url(url):
    '''
    Read data from ``url``.
    
    Returns a 2-tuple of (text, content_type)
    '''
    r = requests.get(url, headers={'User-Agent': random.choice(USER_AGENTS)})
    ct = r.headers.get('content-type')
    return (r.text, ct)


#-------------------------------------------------------------------------------
def seq(what):
    '''
    Make a ``list``-like sequence of ``what``.
    
    If ``what`` is a string or unicode, wrap it in a ``list``.
    '''
    return [what] if is_string(what) else what


_console = logging.StreamHandler()
_console.setFormatter(logging.Formatter(
    '%(asctime)s:%(name)s:%(levelname)s: %(message)s',
    '%Y-%m-%d %H:%M:%S'
))

#-------------------------------------------------------------------------------
def enable_debug_logger(enable=True):
    if enable:
        logger.addHandler(_console)
        logger.setLevel(logging.DEBUG)
    else:
        logger.removeHandler(_console)
        logger.setLevel(logging.WARN)

#-------------------------------------------------------------------------------
def verbose(fmt, *args):
    logger.debug(fmt.format(*args))


#-------------------------------------------------------------------------------
def absolute_filename(filename):
    '''
    Do all those annoying things to arrive at a real absolute path.
    '''
    return os.path.abspath(
        os.path.expandvars(
            os.path.expanduser(filename)
        )
    )


#-------------------------------------------------------------------------------
def write_file(filename, data, mode='w', encoding='utf8'):
    '''
    Write ``data`` to properly encoded file.
    '''
    filename = absolute_filename(filename)
    with codecs.open(filename, mode, encoding=encoding) as fp:
        fp.write(data)


#-------------------------------------------------------------------------------
def read_file(filename, encoding='utf8'):
    '''
    Read ``data`` from properly encoded file.
    '''
    filename = absolute_filename(filename)
    with codecs.open(filename, 'r', encoding=encoding) as fp:
        return fp.read()


#-------------------------------------------------------------------------------
def flatten(lists):
    '''
    Single-level conversion of things to an iterable.
    '''
    return itertools.chain(*lists)


range_re = re.compile(r'''([a-zA-Z]-[a-zA-Z]|\d+-\d+)''', re.VERBOSE)

#-------------------------------------------------------------------------------
def _get_range_run(start, end):
    if start.isdigit():
        fmt = '{}'
        if len(start) > 1 and start[0] == '0':
            fmt = '{{:0>{}}}'.format(len(start))
        return [fmt.format(c) for c in range(int(start), int(end) + 1)]
    
    return [chr(c) for c in range(ord(start), ord(end) + 1)]


#-------------------------------------------------------------------------------
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


#-------------------------------------------------------------------------------
def expand_range_set(sources, range_set=None):
    if is_string(sources):
        sources = [sources]
    
    if not range_set:
        return sources
        
    results = []
    chars = get_range_set(range_set)
    for src in sources:
        results.extend([src.replace('{}', c) for c in chars])
    
    return results


