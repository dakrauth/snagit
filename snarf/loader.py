import os
from urlparse import urlparse, ParseResult

try:
    from urllib.parse import quote_plus as url_quote
except ImportError:
    from urllib import quote_plus as url_quote

try:
    import readline
except ImportError:
    readline = None
    warning.warn('Missing `readline`; no history available', ImportWarning)

from . import utils

verbose = utils.verbose

CACHE_HOME = os.environ.get('XDG_CACHE_HOME', os.path.join(
    os.path.expanduser('~'),
    '.cache'
))


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
def cache_filename(pth):
    if pth.endswith('/'):
        pth = pth[:-1]
        
    pth = url_quote(pth, safe='')
    if not pth.endswith(('.html', '.htm')):
        pth += '.html'


#===============================================================================
class CacheFile(object):
    
    #---------------------------------------------------------------------------
    def __init__(self, cache_dir, urlp):
        self.cache_dir = cache_dir
        urlp if isinstance(urlp, ParseResult) else urlparse(urlp)
        pth = cache_filename(urlp.path[1:] if urlp.path else 'index.html')
        self.dirname = os.path.join(self.cache_dir, urlp.netloc)
        self.filename = os.path.join(self.dirname, pth)
    
    #---------------------------------------------------------------------------
    def read(self):
        data = None
        if os.path.exists(self.filename):
            verbose('Reading from cache file: {}', self.filename)
            data = utils.read_file(self.filename)
            __, data = data.split('\n', 1)
        
        return data
        
    #---------------------------------------------------------------------------
    def write(self, data, from_source):
        verbose('Caching to {}', self.filename)
        if not os.path.exists(self.dirname):
            os.makedirs(self.dirname)
        
        utils.write_file(self.filename, u'<!-- From: {} -->\n{}'.format(from_source, data))
        


#===============================================================================
class Loader(object):
    '''
    A cache loading manager to handle downloading bits from URLs and saving
    them locally.
    
    TODO: add feature to clear cache / force re-download.
    '''
    base_dir = CACHE_HOME
    snarf_dir = '.snarf'
    
    #---------------------------------------------------------------------------
    def __init__(self, use_cache=False):
        self.cache_dir = None
        if use_cache:
            self.use_cache()
    
    #---------------------------------------------------------------------------
    def load_history(base_dir='~', snarf_dir='snarf', filename='history'):
        if not readline:
            return
            
        parent_dir = os.path.join(absolute_filename(base_dir), snarf_dir)
        makedirs(parent_dir)
        histfile = os.path.join(parent_dir, filename)
        try:
            readline.read_history_file(histfile)
            atexit.register(readline.write_history_file, histfile)
        except IOError:
            verbose('Error using `readline` history')
    
    #---------------------------------------------------------------------------
    @property
    def snarf_base(self):
        return os.path.join(self.base_dir, self.snarf_dir)
    
    #---------------------------------------------------------------------------
    def use_cache(self):
        self.cache_dir = os.path.join(self.snarf_base, 'cache')
        makedirs(self.cache_dir)
        verbose('Using cache directory {}', self.cache_dir)
    
    #---------------------------------------------------------------------------
    def load_sources(self, sources, range_set=None):
        if is_string(sources):
            sources = [sources]
        
        if range_set:
            sources = utils.expand_range_set(sources, range_set)
        
        contents = []
        for src in sources:
            verbose('Loading {}', src)
            urlp = urlparse(src)
            data = None
            if urlp.scheme in ('file', ''):
                verbose('Reading from file: {}', urlp.path)
                data = utils.read_file(urlp.path)
            else:
                cache_file = None
                if self.cache_dir:
                    cache_file = CacheFile(self.cache_dir, urlp)
                    data = cache_file.read()

                if data is None:
                    data = utils.read_url(src)
                    verbose('Retrieved {} bytes from {}', len(data), src)
                    if cache_file:
                        cache_file.write(data, src)
            
            verbose('Loaded {} bytes', len(data))
            contents.append(data)
            
        return contents

