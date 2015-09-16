#!/usr/bin/env python
'''
Capture, filter, and extract data from the interwebs
'''
from __future__ import unicode_literals, print_function
import re
import sys
import argparse
from datetime import datetime
from . import utils, script, get_version
from .loader import Loader

verbose = utils.verbose

#-------------------------------------------------------------------------------
def parse_args(args=None):
    parser = argparse.ArgumentParser(prog='snarf', description=__doc__)
    parser.add_argument('source', nargs='*')
    parser.add_argument('-c', '--cache', action='store_true',
        help='for URLs, create or use a local cache of the content')
    parser.add_argument('-v', '--verbose', action='store_true',
        help='increase output verbosity')
    parser.add_argument('-V', '--version', action='store_true',
        help='show version and exit')
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
    parser.add_argument('-i', '--repl', action='store_true',
        help='Enter interactive (REPL) script mode')
    
    return parser, parser.parse_args(args)


#-------------------------------------------------------------------------------
def run_program(prog_args=None):
    parser, args = parse_args(prog_args)
    start = datetime.now()
    if args.pdb:
        utils.pdb.set_trace()
    
    if args.verbose:
        utils.enable_debug_logger()
        verbose('{}', vars(args))
    
    if args.version:
        print('{} - v{}'.format(parser.prog, get_version()))
        sys.exit(0)
    
    loader = Loader(use_cache=args.cache)
    sources = utils.expand_range_set(args.source, args.range_set)
    contents = loader.load_sources(sources)
    code = utils.read_file(args.script) if args.script else ''
    prog = script.Program(code, contents, loader, do_pm=args.pm)
    if code:
        contents = prog.execute()
    
    if args.repl or not args.script:
        contents = prog.repl()
    
    if contents and args.output:
        data = str(contents)
        verbose('Writing {} chars', len(data))
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