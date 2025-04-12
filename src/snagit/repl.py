from pathlib import Path
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.history import FileHistory

from .core import Interpreter
from .exceptions import SnagitQuit


class Repl(Interpreter):
    def __init__(self, *args, **kwargs):
        self.input_handler = kwargs.pop("input_handler", prompt)
        kwargs.setdefault("extensions", []).append("snagit.lib.repl")
        self.prompt_string = kwargs.pop("prompt_string", "> ")
        super().__init__(*args, **kwargs)

    def get_input(self, prompt=None):
        prompt = prompt or self.prompt_string
        return self.input_handler(prompt, history=self.history).strip()

    def repl(self, print_all=False, history="~/.snagit_history"):
        self.history = FileHistory(str(Path(history).expanduser().resolve())) if history else None
        print('Type "help" for more information. Ctrl+c to exit')
        while True:
            try:
                line = self.get_input()
            except (EOFError, KeyboardInterrupt):
                break

            if not line:
                continue

            if line.startswith("!"):
                self.do_debug = True
                line = line[1:].strip()

            if line.startswith("?"):
                line = f"help {line[1:]}"

            try:
                self.execute(line)
            except SnagitQuit:
                break
            finally:
                if print_all:
                    print(str(self.contents))

        return self.contents
