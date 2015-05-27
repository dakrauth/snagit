import re
import os
import codecs
import logging
import itertools
from urlparse import urlparse, ParseResult

try:
    import requests
except ImportError:
    warning.warn('Missing `requests` installation', ImportWarning)
    
try:
    import ipdb as pdb
except ImportError:
    import pdb

logger = logging.getLogger('snarf')

DEFAULT_DELIMITER = '@@@'


#---------------------------------------------------------------------------
def read_url(url, as_text=True):
    '''
    Read data from ``url``. Date can be plain text or bytes.
    '''
    r = requests.get(url)
    return r.text if as_text else r.content


#-------------------------------------------------------------------------------
def is_string(obj):
    '''
    Check if ``obj`` is a string
    '''
    return isinstance(obj, basestring)


#-------------------------------------------------------------------------------
def is_regex(obj):
    '''
    Check if ``obj`` is a regular expression
    
    '''
    return hasattr(obj, 'pattern')


#-------------------------------------------------------------------------------
def seq(what):
    '''
    Make a ``list``-like sequence of ``what``.
    
    If ``what`` is a string or unicode, wrap it in a ``list``.
    '''
    return [what] if is_string(what) else what


#-------------------------------------------------------------------------------
def configure_logger(debug=False):
    if debug:
        console = logging.StreamHandler()
        fmt = logging.Formatter(
            '%(asctime)s:%(name)s:%(levelname)s: %(message)s',
            '%Y-%m-%d %H:%M:%S'
        )
        console.setFormatter(fmt)
        logger.addHandler(console)
        logger.setLevel(logging.DEBUG)
    elif not logger.handlers:
        logger.addHandler(logging.NullHandler())


#-------------------------------------------------------------------------------
def verbose(fmt, *args):
    logger.debug(fmt.format(*args))


#-------------------------------------------------------------------------------
def makedirs(pth):
    '''
    Friendly wrapper for ``os.makedirs``: instead of generating an exception
    for existing ``path``, check first if it exists.
    '''
    if not os.path.exists(pth):
        verbose('Creating directory {}', pth)
        os.makedirs(pth)
        return True
    return False


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


#===============================================================================
class Loader(object):
    '''
    A cache loading manager to handle downloading bits from URLs and saving
    them locally.
    
    TODO: add feature to clear cache / force re-download.
    '''
    #---------------------------------------------------------------------------
    def __init__(self, use_cache=False, **kws):
        self.cache_dir = None
        if use_cache:
            self.use_cache(**kws)
    
    #---------------------------------------------------------------------------
    @staticmethod
    def load_history(base_dir='~', snarf_dir='.snarf', filename='history'):
        try:
            import readline, atexit
        except ImportError:
            return
        
        parent_dir = os.path.join(absolute_filename(base_dir), snarf_dir)
        makedirs(parent_dir)
        histfile = os.path.join(parent_dir, filename)
        
        try:
            readline.read_history_file(histfile)
        except IOError:
            pass
        
        atexit.register(readline.write_history_file, histfile)
        
    #---------------------------------------------------------------------------
    def use_cache(self, base_dir='~', snarf_dir='.snarf', cache_dir='cache'):
        self.cache_dir = os.path.join(absolute_filename(base_dir), snarf_dir, cache_dir)
        if not makedirs(self.cache_dir):
            verbose('Using cache directory {}', self.cache_dir)
        
    #---------------------------------------------------------------------------
    def url_to_cache_filename(self, urlp):
        urlp = urlparse(urlp) if not isinstance(urlp, ParseResult) else urlp
        if urlp.path:
            pth = urlp.path[1:]
        else:
            pth = 'index.html'
        
        pth = '__'.join([s for s in pth.split('/') if s])
        if not pth.endswith(('.html', '.htm')):
            pth += '.html'
        
        dirname = os.path.join(self.cache_dir, urlp.netloc)
        return dirname, os.path.join(dirname, pth)
        
    #---------------------------------------------------------------------------
    def load(self, sources, range_set=None):
        if is_string(sources):
            sources = [sources]
        
        if range_set:
            sources = self.normalize(sources, range_set)
        
        contents = []
        for src in sources:
            verbose('Loading {}', src)
            urlp = urlparse(src)
            data = None
            if urlp.scheme in ('file', ''):
                verbose('Reading from file: {}', urlp.path)
                data = read_file(urlp.path)
        
            elif self.cache_dir:
                dirname, src_munge = self.url_to_cache_filename(urlp)
                if os.path.exists(src_munge):
                    verbose('Reading from cache file: {}', src_munge)
                    data = read_file(src_munge)
                    __, data = data.split('\n', 1)

            if data is None:
                data = read_url(src)
                verbose('Retrieved {} bytes from {}', len(data), src)
                if self.cache_dir:
                    verbose('Caching to {}', src_munge)
                    if not os.path.exists(dirname):
                        os.makedirs(dirname)
                
                    write_file(src_munge, u'<!-- From: {} -->\n{}'.format(src, data))
                
            verbose('Loaded {} bytes', len(data))
            contents.append(data)
            
        return contents

    #---------------------------------------------------------------------------
    def normalize(self, sources, range_set):
        results = []
        chars = get_range_set(range_set)
        for source in sources:
            results.extend([source.replace('{}', c) for c in chars])
        
        return results

