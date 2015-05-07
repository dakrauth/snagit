#!/usr/bin/env python
import re
import os, sys
import logging
import argparse
from collections import OrderedDict
from urlparse import urlparse, ParseResult
from . import snarf

try:
    import ipdb as pdb
except ImportError:
    import pdb


logger = logging.getLogger('snarf')
_simple_msg = '{}'.format


#-------------------------------------------------------------------------------
def verbose(fmt, *args):
    logger.debug(fmt.format(*args))


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
def initialize_cache(base_dir='~', snarf_dir='.snarf', cache_dir='cache'):
    base_dir = os.path.expandvars(os.path.expanduser(base_dir))
    cache_dir = os.path.join(base_dir, snarf_dir, cache_dir)
    
    if not os.path.exists(cache_dir):
        verbose('Creating cache directory {}', cache_dir)
        os.makedirs(cache_dir)
    else:
        verbose('Using cache directory {}', cache_dir)
    return cache_dir


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
                i = ord(seq[-1])
                j = ord(c)
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
class RangeAction(argparse.Action):
    
    #---------------------------------------------------------------------------
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(RangeAction, self).__init__(option_strings, dest, **kwargs)
    
    #---------------------------------------------------------------------------
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, parse_range(values))


#-------------------------------------------------------------------------------
def parse_args(args=None):
    parser = argparse.ArgumentParser(description='Capture, filter, and extract some text')
    parser.add_argument('source', metavar='src', nargs='+')
    parser.add_argument('--cache', action='store_true',
        help='for URLs, create or use a local cache of the content')
    parser.add_argument('-v', '--verbose', action='store_true',
        help='increase output verbosity')
    parser.add_argument('--pdb', action='store_true',
        help='use ipdb or pdb to debug')
    parser.add_argument('--range', action=RangeAction,
        help='a range string to use for running sequences. `source` will replace @@@')
    
    return parser.parse_args(args)


#===============================================================================
class Loader(object):
    
    #---------------------------------------------------------------------------
    def __init__(self, use_cache=False):
        self.cache_dir = initialize_cache() if use_cache else None
        
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
    def load(self, src):
        urlp = urlparse(src)
        if urlp.scheme in ('file', ''):
            verbose('Reading from file: {}', urlp.path)
            return snarf.read_file(urlp.path)
        
        if self.cache_dir:
            dirname, src_munge = self.url_to_cache_filename(urlp)
            if os.path.exists(src_munge):
                verbose('Reading from cache file: {}', src_munge)
                data = snarf.read_file(src_munge)
                __, data = data.split('\n', 1)
                return data

        data = snarf.read_url(src)
        verbose('Retrieved {} bytes from {}', len(data), src)
        if self.cache_dir:
            verbose('Caching to {}', src_munge)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            
            snarf.write_file(src_munge, u'<!-- From: {} -->\n{}'.format(src, data))
        
        return data

#-------------------------------------------------------------------------------
def normalize_sources(sources, range=None):
    items = OrderedDict()
    for src in sources:
        if range:
            for r in range:
                items[src.replace('@@@', r)] = True
        else:
            items[src] = True
    return items.keys()


#-------------------------------------------------------------------------------
def main(prog_args):
    args = parse_args(prog_args)
    if args.pdb:
        pdb.set_trace()
        
    configure_logger(args.verbose)
    verbose('{}', args)
    loader = Loader(args.cache)
    items = normalize_sources(args.source, args.range)
    for item in items:
        verbose('Fetching {}', item)
        loader.load(item)
    


################################################################################
if __name__ == '__main__':
    main(sys.argv[1:])