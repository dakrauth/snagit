#!/usr/bin/env python
import re
import os, sys
import argparse
from datetime import datetime
from . import snarf, utils, script

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
    parser.add_argument('--range-set', dest='range_set',
        help='a range string to use for running sequences.')
    parser.add_argument('--range-token', dest='range_token', default=utils.DEFAULT_RANGE_TOKEN,
        help='token to be replaced in <source> strings when <range> is specified (default: @@@)')
    parser.add_argument('-s', '--script',
        help='script file to execute agains <source>')
    parser.add_argument('-o', '--output',
        help='output resultant content to specified file')
    parser.add_argument('--repl', action='store_true',
        help='Enter REPL script mode')
    
    return parser.parse_args(args)


#-------------------------------------------------------------------------------
def main(prog_args):
    args = parse_args(prog_args)
    start = datetime.now()
    if args.pdb:
        utils.pdb.set_trace()
        
    utils.configure_logger(args.verbose)
    verbose('{}', args)
    loader = utils.Loader()
    if args.cache:
        loader.use_cache()
    
    contents = loader.load(args.source, args.range_set, args.range_token)
    
    if args.repl or args.script:
        code = utils.read_file(args.script) if args.script else ''
        scr = script.Script(code, contents, loader)
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


################################################################################
if __name__ == '__main__':
    main(sys.argv[1:])
