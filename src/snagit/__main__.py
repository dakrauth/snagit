#!/usr/bin/env python
"""
Capture, filter, and extract data from the interwebs
"""

import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime
from . import utils, repl, __version__

logger = logging.getLogger(__name__)


def parse_args(args=None):
    parser = argparse.ArgumentParser(prog="snagit", description=__doc__)
    parser.add_argument("script", nargs="*")
    parser.add_argument("-s", "--source", help="load source material")
    parser.add_argument(
        "-c",
        "--cache",
        action="store_true",
        help="for URLs, create or use a local cache of the content",
    )
    parser.add_argument(
        "-e",
        "--echo",
        action="store_true",
        help="Echo each instruction before execution",
    )
    parser.add_argument(
        "-p",
        "--print",
        action="store_true",
        help="For interactive mode, print current data after each instruction",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
    parser.add_argument("-V", "--version", action="store_true", help="show version and exit")
    parser.add_argument("--pdb", action="store_true", help="use ipdb or pdb to debug")
    parser.add_argument("--pm", action="store_true", help="do post mortem for script exceptions")
    parser.add_argument(
        "--range-set", dest="range_set", help="a range string to use for running sequences."
    )
    parser.add_argument("-o", "--output", help="output result to specified file (stdout if '-')")
    parser.add_argument("--parser", help="Specify BeautifulSoup parser (html.parser)")
    parser.add_argument(
        "-i",
        "--repl",
        action="store_true",
        help="Enter interactive (REPL) script mode (default if script(s) are given)",  # noqa
    )
    parser.add_argument("--exec", help="execute statements")

    return parser, parser.parse_args(args)


def run_program(prog_args=None):
    parser, args = parse_args(prog_args)
    start = datetime.now()
    if args.pdb:
        utils.set_trace()

    logging.basicConfig(
        stream=None,
        level="DEBUG" if args.verbose else "INFO",
        format="[%(asctime)s %(levelname)s %(name)s] %(message)s",
    )

    if args.verbose:
        logger.debug("{}".format(vars(args)))

    if args.version:
        print("{} - v{}".format(parser.prog, __version__))
        sys.exit(0)

    output = ""
    loader = utils.Loader(use_cache=args.cache)
    sources = utils.expand_range_set(args.source, args.range_set)
    contents = loader.load_sources(sources) if sources else ""
    if args.parser:
        utils.config.parser = args.parser

    prog = repl.Repl(contents, loader, do_pm=args.pm, do_echo=args.echo)
    for script in args.script:
        code = Path(script).read_text()
        output += str(prog.execute(code))

    if args.exec:
        output += str(prog.execute(args.exec))

    if args.repl or not (args.script or args.exec):
        output += str(prog.repl(print_all=args.print))

    if output and args.output:
        logger.debug("Writing {} chars".format(len(output)))
        if args.output == "-":
            print(output)
        else:
            Path(args.output).write_text(output)
            logger.debug("Saved to {}".format(args.output))

    logger.debug("Completed in {} seconds".format(datetime.now() - start))
    return contents


def main():
    run_program(sys.argv[1:])
    sys.exit(0)

################################################################################
if __name__ == "__main__":
    main()

