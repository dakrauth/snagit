import re
import sys
import json
import shlex
import logging
import inspect
import importlib
from pathlib import Path
from collections import namedtuple

from .lib import DataProxy
from . import utils
from . import exceptions

logger = logging.getLogger(__name__)


LIBRARIES = ["snagit.lib.program", "snagit.lib.soup", "snagit.lib.text", "snagit.lib.lines"]
InstructionHandler = namedtuple(
    "InstructionHandler", "kind short_descr long_descr short_name long_name"
)


LineInfo = namedtuple("LineInfo", "lineno line tokens")

def repr_ex(w):
    if utils.is_regex(w):
        return '/"{}"/'.format(str(w.pattern))

    return repr(w)


def str_ex(w):
    if utils.is_regex(w):
        return '/"{}"/'.format(str(w.pattern))

    return str(w)


class Instruction(namedtuple("Instruction", "cmd args kwargs linfo")):
    """
    ``Instruction``'s take the form::

        command [arg [arg ...]] [key=arg [key=arg ...]]

    Where ``arg`` can be one of: single quoted string, double quoted string,
    digit, True, False, None, or a simple, unquoted string.
    """

    def __repr__(self):
        args = " ".join([repr_ex(c) for c in self.args]) or None
        kwargs = " ".join(f"{k}={repr_ex(v)}" for k, v in self.kwargs.items()) or None
        return f"<cmd: {self.cmd.lower()}, args={args}, kwargs={kwargs}, linfo={self.linfo}"

    def __str__(self):
        bits = [
            self.cmd.lower(),
            " ".join([str_ex(c) for c in self.args]) or "",
            " ".join(f"{k}={str_ex(v)}" for k, v in self.kwargs.items()) or ""
        ]
        return " ".join(bit for bit in bits if bit)

    @property
    def lineno(self):
        return self.linfo.lineno

    @property
    def line(self):
        return self.linfo.line


class Parser:
    kwarg_re = re.compile(r"(\w+)=(.+)")
    const_dict = {str(val): val for val in [True, False, None]}

    def get_value(self, text):
        if text.isdigit():
            return int(text)

        if text in self.const_dict:
            return self.const_dict[text]

        if len(text) > 1:
            end = text[-1]
            if text.startswith(end) and end == "/":
                return re.compile(utils.escaped(text[1:-1]))

            if end in "'\"":
                if text.startswith(end):
                    return utils.escaped(text[1:-1])

                if text.startswith(f"r{end}"):
                    return re.compile(utils.escaped(text[2:-1]))

        return text

    def lexer(self, line):
        self.lineno += 1
        line = line.strip()
        if line:
            # import pdb; pdb.set_trace()
            tokens = shlex.split(line, comments=True)
            if tokens:
                logger.debug(f"Lexed {len(tokens)} token(s) line {self.lineno}: {tokens}")
                yield LineInfo(self.lineno, line, tokens)

    def parse(self, linfo):
        lineno, line, tokens = linfo
        cmd, *tokens = tokens
        args = []
        kwargs = {}

        for token in tokens:
            m = self.kwarg_re.match(token)
            if m:
                k, v = m.groups()
                kwargs[k] = self.get_value(v)
                continue

            args.append(self.get_value(token))

        return Instruction(cmd.lower(), args, kwargs, linfo)

    def process(self, code, lineno=0):
        """
        Takes the script source code, lexs each line and parses out individial ``Instruction``s
        """
        self.lineno = lineno
        for line in code.splitlines():
            for linfo in self.lexer(line):
                yield self.parse(linfo)


def annotate_function_description(func, kind, short_name, long_name):
    doc = (func.__doc__ or "").strip()
    short, _, long = doc.partition("\n")
    func.snagit = InstructionHandler(
        kind,
        short.strip() or "N/A",
        long.strip(),
        short_name,
        long_name,
    )


class BaseLibrary:
    name = None

    def __init__(self, interprepter):
        self.interpreter = interprepter

    @staticmethod
    def alias(a):
        def wrapper(func):
            func.snagit_alias = a
            return func
        return wrapper


class Contents:
    def __init__(self, contents=None):
        self.stack = []
        self.set_contents(contents)

    def __iter__(self):
        return iter(self.contents)

    def __len__(self):
        return len(self.contents)

    def __str__(self):
        return "\n".join(str(c) for c in self)

    # def __getitem__(self, index):
    #     return self.contents[index]

    def pop(self):
        if self.stack:
            self.contents = self.stack.pop()

    def merge(self):
        if self.contents:
            first = self.contents[0]
            data = first.merge(self.contents)
            self.update(data)

    def struct(self, args, strip=False, name=None):
        self.merge()
        if self.contents:
            data = repr(self.contents[0].struct(args, strip=strip))
            if name:
                data = f"{name} = {data}"

            self.update(f"{data}\n")

    def update(self, contents):
        if not contents:
            return

        if self.contents:
            self.stack.append(self.contents)

        self.set_contents(contents)

    def set_contents(self, contents):
        self.contents = []

        if isinstance(contents, (str, bytes, DataProxy)):
            contents = [contents]

        contents = contents or []
        for ct in contents:
            if isinstance(ct, (str, bytes)):
                ct = DataProxy(ct)

            self.contents.append(ct)


def arg_count(func):
    return func.__func__.__code__.co_argcount


class Interpreter:
    parser_class = Parser
    contents_class = Contents
    loader_class = utils.Loader

    def __init__(self, contents=None, use_cache=False, extensions=None, **kwargs):
        parser_class = kwargs.pop("parser_class", self.parser_class)
        self.parser = parser_class()
        self.contents_class = kwargs.pop("contents_class", self.contents_class)
        self.loader_class = kwargs.pop("loader_class", self.loader_class)

        self.loader = self.loader_class(use_cache)
        self.contents = self.contents_class(contents)
        self.do_debug = kwargs.pop("do_debug", False)
        self.do_pm = kwargs.pop("do_pm", False)
        self.do_echo = kwargs.pop("do_echo", False)

        self.instructions = []
        self.registry = {}
        self.load_libraries(LIBRARIES)
        if extensions:
            self.load_libraries(extensions)

    def load_libraries(self, libs):
        for lib in libs:
            self.load_library(lib)

    def load_library(self, dotted_name):
        *_, lib_name = dotted_name.rpartition(".")
        module = importlib.import_module(dotted_name)

        logger.debug(f"Loading library {dotted_name}")
        Library = module.Library
        lib_name = getattr(Library, "name", lib_name)
        prefix = f"{lib_name}_"
        instance = Library(self)

        def is_instruction(fn):
            return inspect.isfunction(fn) and fn.__name__.startswith(prefix)

        for method_name, method in inspect.getmembers(Library, is_instruction):
            short_name = method_name.replace(prefix, "", 1)
            long_name = f"{lib_name}:{short_name}"

            annotate_function_description(method, lib_name, short_name, long_name)
            instance_function = getattr(instance, method_name)
            self.registry[short_name] = self.registry[long_name] = instance_function
            if hasattr(method, "snagit_alias"):
                self.registry[method.snagit_alias] = instance_function

    def load_source(self, source, use_cache=None):
        ct = self.loader.load_source(source, use_cache=use_cache)
        return ct.decode() if isinstance(ct, bytes) else ct

    def load_sources(self, sources, use_cache=None):
        self.contents.update([self.load_source(source, use_cache=use_cache) for source in sources])

    def listing(self, linenos=False):
        return [
            "{}{}".format("{} ".format(instr.lineno) if linenos else "", instr.line)
            for instr in self.instructions
        ]

    def parse(self, code):
        lineno = self.instructions[-1].linfo.lineno if self.instructions else 0
        instructions = list(self.parser.process(code, lineno))
        self.instructions.extend(instructions)
        return instructions

    def execute(self, code):
        instrs = self.parse(code)
        for instr in instrs:
            if self.do_echo:
                print(
                    f"Executing line {instr.lineno}: "
                    f"{instr.cmd} args={instr.args}, kwargs={instr.kwargs}"
                )
            self._execute_instruction(instr)

        return self.contents

    __call__ = execute

    def execute_script(self, filename, contents=None):
        code = Path(filename).read_text()
        if contents is not None:
            self.contents = self.contents_class(contents)

        return self.execute(code)

    def _execute_instruction(self, instr):
        logger.debug("Executing {}".format(instr.cmd))
        handler = self.registry.get(instr.cmd)
        if not handler:
            raise exceptions.ProgramWarning(
                "Unknown instruction (line {}): {}".format(instr.lineno, instr.cmd)
            )

        do_debug, self.do_debug = self.do_debug, False
        if do_debug:
            utils.set_trace()

        if arg_count(handler) == 3:  # self, args, kwargs
            results = handler(instr.args, instr.kwargs)
            self.contents.update(results)
            return

        results = []
        contents = list(self.contents) or [""]
        for data in contents:
            try:
                result = handler(data, instr.args, instr.kwargs)
            except exceptions.SnagitStopInteration:
                break
            except Exception:
                exc, value, tb = sys.exc_info()
                logger.error(f"Script exception, line {instr.lineno}: {value}")
                if self.do_pm:
                    print("Entering post_mortem")
                    utils.post_mortem(tb)
                else:
                    raise

            if result is not None:
                results.append(result)

        self.contents.update(results)


def execute_code(code, contents="", exec_class=Interpreter):
    intrep = exec_class(contents)
    return str(intrep.execute(code))
