#!/usr/bin/env python
import re
import os, sys
import argparse
from datetime import datetime
from . import snarf, utils, script

verbose = utils.verbose


#===============================================================================
class RangeAction(argparse.Action):
    
    #---------------------------------------------------------------------------
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(RangeAction, self).__init__(option_strings, dest, **kwargs)
    
    #---------------------------------------------------------------------------
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, utils.parse_range(values))


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
    parser.add_argument('-r', '--range', action=RangeAction,
        help='a range string to use for running sequences.')
    parser.add_argument('--range-token', dest='range_token', default=utils.DEFAULT_RANGE_TOKEN,
        help='token to be replaced in <source> strings when <range> is specified (default: @@@)')
    parser.add_argument('-s', '--script',
        help='script file to execute agains <source>')
    parser.add_argument('-o', '--output',
        help='output resultant content to specified file')
    
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
    
    contents = None
    for arg in args.source:
        sources = loader.normalize(arg, args.range, args.range_token)
        contents = loader.load(sources)
    
    if args.script:
        contents = script.execute_script(args.script, contents)

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
