import os
import re
import sys
import json
import shlex
import logging
import inspect
import functools
import importlib
from pprint import pformat
from collections import namedtuple
from traceback import format_tb
from requests.exceptions import RequestException

import strutil
from cachely.loader import Loader

from .lib import library, interpreter_library, DataProxy
from . import utils
from . import core
from . import exceptions

logger = logging.getLogger(__name__)
BASE_LIBS = ['snagit.lib.text', 'snagit.lib.lines', 'snagit.lib.soup']
ReType = type(re.compile(''))


class Instruction(namedtuple('Instruction', 'cmd args kws line lineno')):
    '''
    ``Instruction``'s take the form::

        command [arg [arg ...]] [key=arg [key=arg ...]]

    Where ``arg`` can be one of: single quoted string, double quoted string,
    digit, True, False, None, or a simple, unquoted string.
    '''
    values_pat = r'''
        [rj]?'(?:(\'|[^'])*?)' |
        [r]?"(?:(\"|[^"])*?)"  |
        (\d+)                  |
        (True|False|None)      |
        ([^\s,]+)
    '''

    args_re = re.compile(
        r'''^(
            (?P<kwd>\w[\w\d-]*)=(?P<val>{0}) |
            (?P<arg>{0}|([\s,]+))
        )\s*'''.format(values_pat),
        re.VERBOSE
    )

    value_dict = {'True': True, 'False': False, 'None': None}

    def __str__(self):
        def _repr(w):
            if isinstance(w, ReType):
                return 'r"{}"'.format(str(w.pattern))

            return repr(w)

        return '{}{}{}'.format(
            self.cmd.upper(),
            ' {}'.format(
                ' '.join([_repr(c) for c in self.args]) if self.args else ''
            ),
            ' {}'.format(' '.join(
                '{}={}'.format(k, _repr(v)) for k, v in self.kws.items()
            ) if self.kws else '')
        )

    @classmethod
    def get_value(cls, s):
        if s.isdigit():
            return int(s)
        elif s in cls.value_dict:
            return cls.value_dict[s]
        elif s.startswith(('r"', "r'")):
            return re.compile(utils.escaped(s[2:-1]))
        elif s.startswith("j'"):
            return json.loads(utils.escaped(s[2:-1]))
        elif s.startswith(('"', "'")):
            return utils.escaped(s[1:-1])
        else:
            return s.strip()

    @classmethod
    def parse(cls, line, lineno):
        args = []
        kws = {}
        cmd, text = strutil.splitter(line, expected=2, strip=True)
        cmd = cmd.lower()

        while text:
            m = cls.args_re.search(text)
            if not m:
                break

            gdict = m.groupdict()
            kwd = gdict.get('kwd')
            if kwd:
                kws[kwd] = cls.get_value(gdict.get('val', ''))
            else:
                arg = gdict.get('arg', '').strip()
                if arg != ',':
                    args.append(cls.get_value(arg))

            text = text[len(m.group()):]

        if text:
            raise SyntaxError(
                'Syntax error: "{}" (line {})'.format(text, lineno)
            )

        return cls(cmd, args, kws, line, lineno)


def lexer(code, lineno=0):
    '''
    Takes the script source code, scans it, and lexes it into
    ``Instructions``
    '''
    for chars in code.splitlines():
        lineno += 1
        line = chars.rstrip()
        if not line or line.lstrip().startswith('#'):
            continue

        logger.debug('Lexed {} byte(s) line {}'.format(len(line), chars))
        yield Instruction.parse(line, lineno)


def load_libraries(extensions=None):

    if isinstance(extensions, str):
        extensions = [extensions]

    libs = BASE_LIBS + (extensions or [])
    for lib in libs:
        importlib.import_module(lib)


class Interpreter:

    def __init__(
        self,
        contents=None,
        loader=None,
        use_cache=False,
        do_pm=False,
        extensions=None
    ):
        self.use_cache = use_cache
        self.loader = loader if loader else Loader(use_cache=use_cache)
        self.contents = Contents(contents)
        self.do_debug = False
        self.do_pm = do_pm
        self.instructions = []
        load_libraries(extensions)

    def load_sources(self, sources, use_cache=None):
        use_cache = self.use_cache if use_cache is None else bool(use_cache)
        contents = self.loader.load_sources(sources)
        self.contents.update([
            ct.decode() if isinstance(ct, bytes) else ct for ct in contents
        ])

    def listing(self, linenos=False):
        items = []
        for instr in self.instructions:
            items.append('{}{}'.format(
                '{} '.format(instr.lineno) if linenos else '',
                instr.line
            ))

        return items

    def lex(self, code):
        lineno = self.instructions[-1].lineno if self.instructions else 0
        instructions = list(lexer(code, lineno))
        self.instructions.extend(instructions)
        return instructions

    def execute(self, code):
        for instr in self.lex(code):
            try:
                self._execute_instruction(instr)
            except exceptions.ProgramWarning as why:
                print(why)

        return self.contents

    def _load_handler(self, instr):
        if instr.cmd in library.registry:
            func = library.registry[instr.cmd]
            return self.contents, (func, instr.args, instr.kws)

        elif instr.cmd in interpreter_library.registry:
            func = interpreter_library.registry[instr.cmd]
            return func, (self, instr.args, instr.kws)

        raise exceptions.ProgramWarning(
            'Unknown instruction (line {}): {}'.format(instr.lineno, instr.cmd)
        )

    def _execute_instruction(self, instr):
        logger.debug('Executing {}'.format(instr.cmd))
        handler, args = self._load_handler(instr)

        do_debug, self.do_debug = self.do_debug, False
        if do_debug:
            utils.pdb.set_trace()

        try:
            handler(*args)
        except Exception:
            exc, value, tb = sys.exc_info()
            if self.do_pm:
                logger.error(
                    'Script exception, line {}: {} (Entering post_mortem)'.format(  # noqa
                        instr.lineno,
                        value
                    )
                )
                utils.pdb.post_mortem(tb)
            else:
                raise


def execute_script(filename, contents=''):
    code = utils.read_file(filename)
    return execute_code(code, contents)


def execute_code(code, contents=''):
    intrep = Interpreter(contents)
    return str(intrep.execute(code))


class Contents:

    def __init__(self, contents=None):
        self.stack = []
        self.set_contents(contents)

    def __iter__(self):
        return iter(self.contents)

    def __len__(self):
        return len(self.contents)

    def __str__(self):
        return '\n'.join(str(c) for c in self)

    # def __getitem__(self, index):
    #     return self.contents[index]

    def pop(self):
        if self.stack:
            self.contents = self.stack.pop()

    def __call__(self, func, args, kws):
        contents = []
        for data in self:
            result = func(data, args, kws)
            contents.append(result)

        self.update(contents)

    def merge(self):
        if self.contents:
            first = self.contents[0]
            data = first.merge(self.contents)
            self.update([data])

    def update(self, contents):
        if self.contents:
            self.stack.append(self.contents)

        self.set_contents(contents)

    def set_contents(self, contents):
        self.contents = []

        if isinstance(contents, (str, bytes)):
            contents = [contents]

        contents = contents or []
        for ct in contents:
            if isinstance(ct, (str, bytes)):
                ct = DataProxy(ct)
            
            self.contents.append(ct)
