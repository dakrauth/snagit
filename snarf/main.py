#!/usr/bin/env python
import re
import os, sys
import argparse
from datetime import datetime
from . import utils, script
from .loader import Loader
verbose = utils.verbose


#-------------------------------------------------------------------------------
def parse_args(args=None):
    parser = argparse.ArgumentParser(description='Capture, filter, and extract some text')
    parser.add_argument('source', nargs='*')
    parser.add_argument('-C', '--cache', action='store_true',
        help='for URLs, create or use a local cache of the content')
    parser.add_argument('-v', '--verbose', action='store_true',
        help='increase output verbosity')
    parser.add_argument('--pdb', action='store_true',
        help='use ipdb or pdb to debug')
    parser.add_argument('--pm', action='store_true',
        help='do post mortem for script exceptions')
    parser.add_argument('--range-set', dest='range_set',
        help='a range string to use for running sequences.')
    parser.add_argument('-s', '--script',
        help='script file to execute agains <source>')
    parser.add_argument('-o', '--output',
        help='output resultant content to specified file')
    parser.add_argument('--repl', action='store_true',
        help='Enter REPL script mode')
    
    return parser.parse_args(args)


#-------------------------------------------------------------------------------
def run_program(prog_args=None):
    args = parse_args(prog_args)
    start = datetime.now()
    if args.pdb:
        utils.pdb.set_trace()
        
    if args.verbose:
        utils.enable_debug_logger()
    
    verbose('{}', args)
    loader = Loader()
    if args.cache:
        loader.use_cache()
    
    sources = utils.expand_range_set(args.source, args.range_set)
    contents = loader.load_sources(sources)
    
    if args.repl or args.script:
        code = utils.read_file(args.script) if args.script else ''
        scr = script.Program(code, contents, loader, do_pm=args.pm)
        if code:
            contents = scr.execute()
    
        if args.repl:
            contents = scr.repl()
    
    if args.output and contents:
        data = '\n'.join([unicode(c) for c in contents])
        verbose('Writing {} bytes', len(data))
        if args.output == '-':
            sys.stdout.write(data.encode('utf8') + '\n')
        else:
            utils.write_file(args.output, data)
            verbose('Saved to {}', args.output)
    
    verbose('Completed in {} seconds', datetime.now() - start)
    return contents


#-------------------------------------------------------------------------------
def main():
    run_program(sys.argv[1:])


################################################################################
if __name__ == '__main__':
    main()
