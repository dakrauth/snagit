import re
import sys
import json
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


class Instruction(namedtuple("Instruction", "cmd args kws line lineno")):
    """
    ``Instruction``'s take the form::

        command [arg [arg ...]] [key=arg [key=arg ...]]

    Where ``arg`` can be one of: single quoted string, double quoted string,
    digit, True, False, None, or a simple, unquoted string.
    """

    values_pat = r"""
        [rj]?'(?:(\'|[^'])*?)' |
        [r]?"(?:(\"|[^"])*?)"  |
        (\d+)                  |
        (True|False|None)      |
        ([^\s,]+)
    """

    args_re = re.compile(
        r"""^(
            (?P<kwd>\w[\w\d-]*)=(?P<val>{0}) |
            (?P<arg>{0}|([\s,]+))
        )\s*""".format(values_pat),
        re.VERBOSE,
    )

    value_dict = {str(val): val for val in [True, False, None]}

    def __str__(self):
        def _repr(w):
            if utils.is_regex(w):
                return 'r"{}"'.format(str(w.pattern))

            return repr(w)

        return "{}{}{}".format(
            self.cmd.upper(),
            " {}".format(" ".join([_repr(c) for c in self.args]) if self.args else ""),
            " {}".format(
                " ".join("{}={}".format(k, _repr(v)) for k, v in self.kws.items())
                if self.kws
                else ""
            ),
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
        cmd, text = utils.splitter(line, expected=2, strip=True)
        cmd = cmd.lower()

        while text:
            m = cls.args_re.search(text)
            if not m:
                break

            gdict = m.groupdict()
            kwd = gdict.get("kwd")
            if kwd:
                kws[kwd] = cls.get_value(gdict.get("val", ""))
            else:
                arg = gdict.get("arg", "").strip()
                if arg != ",":
                    args.append(cls.get_value(arg))

            text = text[len(m.group()) :]

        if text:
            raise SyntaxError('Syntax error: "{}" (line {})'.format(text, lineno))

        return cls(cmd, args, kws, line, lineno)

    @classmethod
    def lexer(cls, code, lineno=0):
        """
        Takes the script source code, scans it, and lexes it into
        ``Instructions``
        """
        for chars in code.splitlines():
            lineno += 1
            line = chars.rstrip()
            if not line or line.lstrip().startswith("#"):
                continue

            logger.debug("Lexed {} byte(s) line {}".format(len(line), chars))
            yield cls.parse(line, lineno)


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

    # def __call__(self, func, args, kws):
    #     contents = []
    #     for data in self:
    #         result = func(data, args, kws)
    #         if result is not None:
    #             contents.append(result)
    #     self.update(contents)

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


class Interpreter:
    instruction_class = Instruction
    contents_class = Contents
    loader_class = utils.Loader

    def __init__(self, contents=None, use_cache=False, extensions=None, **kwargs):
        self.instruction_class = kwargs.pop("instruction_class", self.instruction_class)
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
            short_name = method_name.replace(prefix, "", count=1)
            long_name = f"{lib_name}:{short_name}"

            annotate_function_description(method, lib_name, short_name, long_name)
            self.registry[short_name] = self.registry[long_name] = getattr(instance, method_name)

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

    def lex(self, code):
        lineno = self.instructions[-1].lineno if self.instructions else 0
        instructions = list(self.instruction_class.lexer(code, lineno))
        self.instructions.extend(instructions)
        return instructions

    def execute(self, code):
        instrs = self.lex(code)
        for instr in instrs:
            if self.do_echo:
                print(
                    f"Executing line {instr.lineno}: "
                    f"{instr.cmd} args={instr.args}, kwargs={instr.kws}"
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

        contents = list(self.contents)
        contents = contents or [""]
        results = []
        # import pdb; pdb.set_trace()
        for data in contents:
            try:
                result = handler(data, instr.args, instr.kws)
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

        if results:
            self.contents.update(results)


def execute_code(code, contents="", exec_class=Interpreter):
    intrep = exec_class(contents)
    return str(intrep.execute(code))
