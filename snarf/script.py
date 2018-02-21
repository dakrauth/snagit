import os
import re
import sys
import json
import shlex
import logging
import inspect
import functools
import traceback
from pprint import pformat
from requests.exceptions import RequestException

import strutil
from cachely.loader import Loader
from prompt_toolkit.shortcuts import get_input
from prompt_toolkit.history import FileHistory

from . import utils
from . import core
from . import exceptions

logger = logging.getLogger(__name__)


class Instruction:
    '''
    ``Instruction``'s take the form::

        command [arg [arg ...]] [key=arg [key=arg ...]]

    Where ``arg`` can be one of: single quoted string, double quoted string,
    digit, True, False, None, or a simple, unquoted string.
    '''
    values_pat = r'''
        r?'(?:(\'|[^'])*?)'   |
        r?"(?:(\"|[^"])*?)"   |
        (\d+)                 |
        (True|False|None)     |
        ([\S]+)
    '''

    args_re = re.compile(
        r'''^(
            (?P<kwd>\w+)=(?P<val>{0}) |
            (?P<arg>{0})
        )\s*'''.format(values_pat),
        re.VERBOSE
    )
    value_dict = {'True': True, 'False': False, 'None': None}

    def __init__(self, program, line, lineno):
        self.program = program
        self.lineno = lineno
        self.parse(line)

    def __repr__(self):
        return '<Instruction({}): {}, {}>'.format(self.cmd, self.args, self.kws)

    def get_value(self, s):
        if s.isdigit():
            return int(s)
        elif s in self.value_dict:
            return self.value_dict[s]
        elif s.startswith(('r"', "r'")):
            return re.compile(utils.escaped(s[2:-1]))
        elif s.startswith(('"', "'")):
            return utils.escaped(s[1:-1])
        else:
            return s.strip()

    def parse(self, text):
        self.args = []
        self.kws = {}
        self.cmd, text = strutil.splitter(text, expected=2, strip=True)

        if not text:
            return

        while text:
            m = self.args_re.search(text)
            if not m:
                break

            gdict = m.groupdict()
            kwd = gdict.get('kwd')
            if kwd:
                self.kws[kwd] = self.get_value(gdict.get('val', ''))
            else:
                arg = gdict.get('arg', '')
                if arg != ',':
                    self.args.append(self.get_value(arg))

            text = text[len(m.group()):]

        if text:
            raise SyntaxError('Syntax error: "{}" (line {})'.format(text, self.lineno))


class Script:
    '''
    ``Script`` takes the script source code, scans it, and compiles it into
    ``Instructions``
    '''

    def __init__(self, code=''):
        self.lineno = 1
        self.code = ''
        self.lines = []
        self.instructions = []
        if code:
            self.compile(code)

    def listing(self):
        return [line for line in self.code.splitlines() if line]

    def compile(self, code):
        self.code += '\n' + code if self.code else code

        lines = self.scan(code)
        self.lines += lines

        instructions = [Instruction(self, line, lineno) for line, lineno in lines]
        self.instructions += instructions

        return instructions

    def scan(self, text):
        lines = []
        for line in text.splitlines():
            line = line.rstrip()
            if not line or line.lstrip().startswith('#'):
                continue
            lines.append((line, self.lineno))
            self.lineno += 1

        logger.debug('Scanned {} lines from {} bytes'.format(len(lines), len(text)))
        return lines


class Commands:

    commands = {}

    @classmethod
    def get(cls, cmd=None):
        if isinstance(cmd, str):
            return cls.commands.get(cmd, None)

        cmds = []
        for name in sorted(cls.commands.keys()):
            if not cmd or name in cmd:
                cmds.append(cls.commands[name])

        return cmds

    @staticmethod
    def register_handler(kind):
        '''
        Create a decorator for the given ``Bits``-derived content handler.
        '''
        def decorator(func):
            func.kind = kind
            name = func.__name__.replace('_cmd', '')
            Commands.commands[name] = func
            return func
        return decorator


prog_handler = Commands.register_handler('Program')
html_handler = Commands.register_handler('Soup')
text_handler = Commands.register_handler('Text')
line_handler = Commands.register_handler('Lines')


@prog_handler
def list_cmd(context, args, kws):
    '''
    List all lines of source code if not empty.
    '''
    print(utils.join(context.script.listing()))


@prog_handler
def help_cmd(context, args, kws):
    '''
    Display help on available commands.
    '''
    cmds = Commands.get(args or None)
    format = '    {} ({})'.format
    if not args:
        print('Commands:')
        print(utils.join(format(cmd.__name__, cmd.kind) for cmd in cmds))
    else:
        for cmd in cmds:
            print(format(cmd.__name__, cmd.kind))
            print(cmd.__doc__ if cmd.__doc__ else '')


@prog_handler
def combine_cmd(context, args, kws):
    '''
    Combine all contents into a single content.
    '''
    context('combine')


@prog_handler
def serialize_cmd(context, args, kws):
    '''
    Serialize content data into either 'python' or 'json'.
    '''
    #context('combine')
    context('serialize', **kws)


@prog_handler
def cache_cmd(context, args, kws):
    '''
    Enable caching.
    '''
    context.loader.use_cache = True


@prog_handler
def load_cmd(context, args, kws):
    '''
    Load new resource(s).
    '''
    range_set = kws.get('range_set', kws.get('range'))
    sources = utils.expand_range_set(args, range_set)
    try:
        contents = context.loader.load_sources(sources)
    except RequestException as exc:
        print('ERROR: {}'.format(exc))
    else:
        context('update', contents)


@prog_handler
def load_all_cmd(context, args, kws):
    '''
    Load new resource(s) from current content contents array.
    '''
    sources = []
    for content in context.contents:
        sources.extend(list(content))

    load(context).execute(sources, kws)


@prog_handler
def debug_cmd(context, args, kws):
    '''
    Enable a debugging breakpoint.
    '''
    context.do_debug = True


@prog_handler
def echo_cmd(context, args, kws):
    print('ARGS >>> {}\nKWDS >>> {}'.format(args, kws))


@prog_handler
def run_cmd(context, args, kws):
    code = utils.read_file(args[0])
    context.execute_code(code)


@prog_handler
def write_cmd(context, args, kws):
    '''
    Dumps the text representation of all content to the specified file.
    '''
    utils.write_file(args[0], str(context.contents))


@prog_handler
def print_cmd(context, args, kws):
    '''
    Print out the text representation of the content.
    '''
    print(str(context.contents))


@prog_handler
def end_cmd(context, args, kws):
    context('end')


@prog_handler
def convert(context, args, kws):
    context('convert', args[0])

# Lines methods

@line_handler
def skip_to_cmd(context, args, kws):
    '''
    Skip lines until finding a matching line.
    '''
    context('skip_to', args[0], **kws)


@line_handler
def read_until_cmd(context, args, kws):
    '''
    Save lines until finding a matching line.
    '''
    context('read_until', args[0], **kws)


@line_handler
def strip_cmd(context, args, kws):
    '''
    Strip whitespace from content.
    '''
    context('strip')


@line_handler
def matches_cmd(context, args, kws):
    '''
    Save lines matching the input.
    '''
    context('matches', args[0], **kws)


@line_handler
def compress_cmd(context, args, kws):
    '''
    Strip, split, and rejoin each line using a single space.
    '''
    context('compress')


@line_handler
def format_cmd(context, args, kws):
    '''
    Format each line, where the current line is passed using {}.
    '''
    context('format', args[0])

# Text methods

@text_handler
def remove_cmd(context, args, kws):
    '''
    Remove each string argument from the text.
    '''
    context('remove_each', args, **kws)


@text_handler
def replace_cmd(context, args, kws):
    '''
    Replace each string argument with the last given argument as the replacement.
    '''
    args = args[:]
    replacement = args.pop()
    args = [(a, replacement) for a in args]
    context('replace_each', args, **kws)


# HTML methods

@html_handler
def extract_empty_cmd(context, args, kws):
    '''
    Remove empty tags
    '''
    context('extract_empty', args)


@html_handler
def remove_attrs_cmd(context, args, kws):
    '''
    Removes the specified attributes from all elements.
    '''
    context('remove_attrs', args, **kws)


@html_handler
def unwrap_cmd(context, args, kws):
    '''
    Replace an element with its child contents.
    '''
    context('unwrap', args, **kws)


@html_handler
def unwrap_attr_cmd(context, args, kws):
    '''
    Replace an element with the content for a specified attribute.
    '''
    context('unwrap_attr', args[0], args[1])


@html_handler
def extract_cmd(context, args, kws):
    '''
    Removes the specified elements.
    '''
    context('extract', args, **kws)


@html_handler
def select_cmd(context, args, kws):
    '''
    Whittle down elements to those matching the CSS selection.
    '''
    context('select', args[0], limit=kws.get('limit'))


@html_handler
def replace_tag_cmd(context, args, kws):
    '''
    Replace the specified tag with some plain text.
    '''
    context('replace_with', args[0], args[1])


@html_handler
def collapse_cmd(context, args, kws):
    '''
    Given a CSS selector, combine multiple whitespace chars into a single space and trim.
    '''
    context('collapse', *args, **kws)


class Program:

    def __init__(self, code='', contents=None, loader=None, use_cache=False, do_pm=False):
        self.loader = loader if loader else Loader(use_cache=use_cache)
        self.history = FileHistory('.snarf_history')
        self.contents = core.Contents(contents)
        self.do_debug = False
        self.do_pm = do_pm
        self.script = Script(code)

    def get_input(self, prompt='> '):
        return get_input(prompt, history=self.history).strip()

    def repl(self, print_all=False):
        print('Type "help" for more information. Ctrl+c to exit')
        while True:
            try:
                line = self.get_input()
            except (EOFError, KeyboardInterrupt):
                break

            if not line:
                continue

            if line.startswith('!'):
                self.do_debug = True
                line = line[1:].strip()

            if line.startswith('?'):
                line = 'help ' + line[1:]

            self.execute_code(line)
            if print_all:
                print_cmd(self).execute((), {})

        return self.contents

    def execute_code(self, line):
        instrs = self.script.compile(line)
        try:
            self.execute(instrs)
        except exceptions.ProgramWarning as why:
            print(why)

    def _execute_instruction(self, instr):
        logger.debug('Executing {}'.format(instr.cmd))
        cmd_func = Commands.get(instr.cmd)
        if cmd_func is None:
            raise exceptions.ProgramWarning(
                'Unknown script instr (line {}): {}'.format(
                    instr.lineno,
                    instr.cmd
                )
            )

        do_debug, self.do_debug = self.do_debug, False
        error = None
        if do_debug:
            utils.pdb.set_trace()

        try:
            cmd_func(self, instr.args, instr.kws)
        except:
            exc, value, tb = sys.exc_info()
            if self.do_pm:
                logger.error(
                    'Script exception, line {}: {} (Entering post_mortem)'.format(
                        instr.lineno,
                        value
                    )
                )
                utils.pdb.post_mortem(tb)
            else:
                raise exceptions.ProgramError(
                    'Line {}: {}'.format(instr.lineno, value)
                ) from exc

    def execute(self, instructions=None):
        instructions = instructions or self.script.instructions
        for instr in instructions:
            self._execute_instruction(instr)

        return self.contents


def execute_script(filename, contents):
    code = utils.read_file(filename)
    scr = Program(code, contents)
    return scr.execute()
