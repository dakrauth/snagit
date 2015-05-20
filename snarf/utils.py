import re
import os
import codecs
import logging
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

DEFAULT_RANGE_TOKEN = '@@@'


#---------------------------------------------------------------------------
def read_url(url, as_text=True):
    r = requests.get(url)
    return r.text if as_text else r.content


#-------------------------------------------------------------------------------
def is_string(obj):
    '''
    Check if obj is a string
    '''
    return isinstance(obj, basestring)


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
    if not os.path.exists(pth):
        verbose('Creating directory {}', pth)
        os.makedirs(pth)
        return True
    return False


#-------------------------------------------------------------------------------
def absolute_filename(filename):
    return os.path.abspath(
        os.path.expandvars(
            os.path.expanduser(filename)
        )
    )


#-------------------------------------------------------------------------------
def write_file(filename, data, mode='w', encoding='utf8'):
    filename = absolute_filename(filename)
    with codecs.open(filename, mode, encoding=encoding) as fp:
        fp.write(data)


#-------------------------------------------------------------------------------
def read_file(filename, encoding='utf8'):
    filename = absolute_filename(filename)
    with codecs.open(filename, 'r', encoding=encoding) as fp:
        return fp.read()



range_re = re.compile(r'''([a-zA-Z]-[a-zA-Z]|\d+-\d+)''', re.VERBOSE)

#-------------------------------------------------------------------------------
def get_range_run(start, end):
    if start.isdigit():
        fmt = '{}'
        if len(start) > 1 and start[0] == '0':
            fmt = '{{:0>{}}}'.format(len(start))
        return [fmt.format(c) for c in range(int(start), int(end) + 1)]
    
    return [chr(c) for c in range(ord(start), ord(end) + 1)]


#-------------------------------------------------------------------------------
def get_range_set(text):
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
        values.extend(get_range_run(start, end))

    return values


#===============================================================================
class Loader(object):
    
    #---------------------------------------------------------------------------
    def __init__(self):
        self.cache_dir = None
    
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
    def load(self, sources, range=None, token=DEFAULT_RANGE_TOKEN):
        if is_string(sources):
            sources = [sources]
        
        normalized = []
        for src in sources:
            normalized.extend(self.normalize(src, range, token))
        
        contents = []
        for src in normalized:
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
    def normalize(self, source, range_set=None, token=DEFAULT_RANGE_TOKEN):
        if range_set:
            return [source.replace(token, r) for r in get_range_set(range_set)]
        
        return [source]

