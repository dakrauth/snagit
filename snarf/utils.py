import os
import codecs
import logging
from urlparse import urlparse, ParseResult

try:
    import requests
except ImportError:
    import warnings
    warning.warn('Missing `requests` installation', ImportWarning)
    
    #---------------------------------------------------------------------------
    def read_url(*args, **kws):
        raise RuntimeError('Unavailable - check environment for proper 3rd party installs')
    
else:

    #---------------------------------------------------------------------------
    def read_url(url, as_text=True):
        r = requests.get(url)
        return r.text if as_text else r.content


try:
    import ipdb as pdb
except ImportError:
    import pdb

logger = logging.getLogger('snarf')

DEFAULT_RANGE_TOKEN = '@@@'

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


#-------------------------------------------------------------------------------
def parse_range(s):
    lst = list(s)
    if len(lst) < 3:
        return lst

    seq = []
    found = False
    for c in lst:
        if c == '-':
            found = True
        else:
            if found:
                i, j = ord(seq[-1]), ord(c)
                inc = 1 if i <= j else -1
                for k in range(i + inc, j + inc, inc):
                    seq.append(chr(k))
                found = False
            else:
                seq.append(c)
    if found:
        seq.append('-')
    return seq


#===============================================================================
class Loader(object):
    
    #---------------------------------------------------------------------------
    def __init__(self):
        self.cache_dir = None
    
    #---------------------------------------------------------------------------
    def use_cache(self, base_dir='~', snarf_dir='.snarf', cache_dir='cache'):
        self.cache_dir = os.path.join(
            absolute_filename(base_dir),
            snarf_dir,
            cache_dir
        )
        
        if not makedirs(self.cache_dir):
            verbose('Using cache directory {}', self.cache_dir)
        
    #---------------------------------------------------------------------------
    def url_to_cache_filename(self, urlp):
        urlp = urlparse(urlp) if not isinstance(urlp, ParseResult) else urlp
        if urlp.path:
            pth = urlp.path[1:]
        else:
            pth = 'index.html'
        
        pth = '__'.join(os.path.split(pth))
        if not pth.endswith(('.html', '.htm')):
            pth += '.html'
        
        dirname = os.path.join(self.cache_dir, urlp.netloc)
        return dirname, os.path.join(dirname, pth)
        
    #---------------------------------------------------------------------------
    def load(self, sources):
        if is_string(sources):
            sources = [sources]
        
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
                
                    snarf.write_file(src_munge, u'<!-- From: {} -->\n{}'.format(src, data))
                
            verbose('Loaded {} bytes', len(data))
            contents.append(data)
            
        return contents

    #---------------------------------------------------------------------------
    def normalize(self, source, range_=None, range_token=DEFAULT_RANGE_TOKEN):
        sources = []
        if range_:
            for r in range_:
                sources.append(source.replace(range_token, r))
        else:
            sources.append(source)

        return sources

