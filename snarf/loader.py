from __future__ import unicode_literals
import os
import atexit
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
def safe_filepath(pth, default='index', suffix='.html'):
    if pth:
        pth = pth.strip('/')

    pth = url_quote(pth, safe='') if pth else default
    if not pth.endswith(suffix):
        pth += suffix
        
    return pth


#===============================================================================
class Loader(object):
    '''
    A cache loading manager to handle downloading bits from URLs and saving
    them locally.
    
    TODO: add feature to clear cache / force re-download.
    '''
    
    #---------------------------------------------------------------------------
    def __init__(self, use_cache=False, cache_base=CACHE_HOME, directory='snarf'):
        self.snarf_dir = os.path.join(utils.absolute_filename(cache_base), directory)
        self.cache_dir = os.path.join(self.snarf_dir, 'cache')
        self.use_cache = use_cache
    
    #---------------------------------------------------------------------------
    @property
    def use_cache(self):
        return self._use_cache
    
    #---------------------------------------------------------------------------
    @use_cache.setter
    def use_cache(self, value):
        if value:
            self.get_directory(self.cache_dir)
            
        self._use_cache = value
        
    #---------------------------------------------------------------------------
    def get_directory(self, pth):
        if not os.path.exists(pth):
            verbose('Creating directory {}', pth)
            makedirs(pth)
        return pth
        
    #---------------------------------------------------------------------------
    def load_history(self, filename='history'):
        if not readline:
            return
        
        base = self.get_directory(self.snarf_dir)
        histfile = os.path.join(base, filename)
        verbose('Reading history file: {}'.format(histfile))
        try:
            readline.read_history_file(histfile)
        except IOError as e:
            verbose('Error using `readline` history: {}'.format(e))
        else:
            verbose('History file at {} bytes'.format(readline.get_current_history_length()))
            atexit.register(readline.write_history_file, histfile)
    
    #---------------------------------------------------------------------------
    def load_sources(self, sources):
        sources = sources or []
        contents = []
        for src in sources:
            verbose('Loading {}', src)
            data = self.load_source(src)
            contents.append(data)
            
        return contents

    #---------------------------------------------------------------------------
    def load_source(self, url):
        parse_result = urlparse(url)
        if self.use_cache:
            dirname = os.path.join(self.cache_dir, parse_result.netloc)
            filename = os.path.join(dirname, safe_filepath(parse_result.path))
        else:
            dirname = filename = None
        
        data = None
        if parse_result.scheme.lower() in ('file', ''):
            verbose('Reading from file: {}', parse_result.path)
            data = utils.read_file(parse_result.path)
        elif filename and os.path.exists(filename):
            verbose('Reading from cache file: {}', filename)
            data = utils.read_file(filename)
            __, data = data.split('\n', 1)
        else:
            data, content_type = utils.read_url(url)
            verbose('Retrieved {} bytes from {}', len(data), url)
            if filename:
                if not os.path.exists(dirname):
                    os.makedirs(dirname)
                
                utils.write_file(filename, '<!-- From: {} -->\n{}'.format(url, data))
        
        return data

