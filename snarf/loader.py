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


#---------------------------------------------------------------------------
def get_directory(pth):
    if not os.path.exists(pth):
        verbose('Creating directory {}', pth)
        os.makedirs(pth)
    return pth


#-------------------------------------------------------------------------------
def safe_filepath(pth, default='index', suffix='.html'):
    if pth:
        pth = pth.strip('/')

    pth = url_quote(pth, safe='') if pth else default
    if not pth.endswith(suffix):
        pth += suffix
        
    return pth


#===============================================================================
class FilePath(object):
    
    #---------------------------------------------------------------------------
    def __init__(self, *bits):
        if len(bits) == 1:
            self.filepath = bits[0]
            self.dirname = os.path.dirname(self.filepath)
        else:
            self.dirname = os.path.join(*bits[:-1])
            self.filepath = os.path.join(self.dirname, bits[-1])

    #---------------------------------------------------------------------------
    def exists(self):
        return os.path.exists(self.filepath)

    #---------------------------------------------------------------------------
    def read(self):
        verbose('Reading from cache file: {}', self.filepath)
        return utils.read_file(self.filepath)
        
    #---------------------------------------------------------------------------
    def write(self, data):
        get_directory(self.dirname)
        utils.write_file(self.filepath, data)


#===============================================================================
class CacheFilePath(FilePath):
    
    #---------------------------------------------------------------------------
    def read(self):
        data = super(CacheFilePath, self).read()
        return data.split('\n', 1)[1]

    #---------------------------------------------------------------------------
    def write(self, data, url):
        super(CacheFilePath, self).write('<!-- From: {} -->\n{}'.format(url, data))


#===============================================================================
class CacheManager(object):
    
    #---------------------------------------------------------------------------
    def __init__(self, dir_name='cache', cache_base=None):
        cache_base = cache_base or utils.get_config('cache_home')
        self.cache_dir = os.path.join(cache_base, dir_name)

    #---------------------------------------------------------------------------
    def get_filepath(self, netloc, pth):
        return CacheFilePath(self.cache_dir, netloc, safe_filepath(pth))

    #---------------------------------------------------------------------------
    def iter_cache(self):
        pass
        
#===============================================================================
class Loader(object):
    '''
    A cache loading manager to handle downloading bits from URLs and saving
    them locally.
    
    TODO: add feature to clear cache / force re-download.
    '''
    
    #---------------------------------------------------------------------------
    def __init__(self, use_cache=False, cache_base=None, directory='snarf'):
        cache_base = cache_base or utils.get_config('cache_home')
        self.snarf_dir = os.path.join(utils.absolute_filename(cache_base), directory)
        self.cache_dir = os.path.join(self.snarf_dir, 'cache')
        self.cache = CacheManager(cache_base=self.snarf_dir)
        self.use_cache = use_cache
    
    #---------------------------------------------------------------------------
    @property
    def use_cache(self):
        return self._use_cache
    
    #---------------------------------------------------------------------------
    @use_cache.setter
    def use_cache(self, value):
        if value:
            get_directory(self.cache_dir)
        self._use_cache = value
        
    #---------------------------------------------------------------------------
    def load_history(self, filename='history'):
        if not readline:
            return
        
        base = get_directory(self.snarf_dir)
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
    def load_sources(self, sources, force_reload=False):
        sources = sources or []
        contents = []
        for src in sources:
            verbose('Loading {}', src)
            data = self.load_source(src)
            contents.append(data)
            
        return contents

    #---------------------------------------------------------------------------
    def load_source(self, url, force_reload=False):
        purl = urlparse(url)
        data = None
        if purl.scheme.lower() in ('file', ''):
            verbose('Reading from file: {}', purl.path)
            data = utils.read_file(purl.path)
        else:
            cfp = None
            if self.use_cache:
                cfp = self.cache.get_filepath(purl.netloc, purl.path)
                
            if not force_reload and cfp and cfp.exists():
                data = cfp.read()
            else:
                data, content_type = utils.read_url(url)
                verbose('Retrieved {} bytes from {}', len(data), url)
                cfp and cfp.write(data, url)
        
        return data

