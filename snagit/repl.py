from prompt_toolkit.shortcuts import get_input
from prompt_toolkit.history import FileHistory

from .core import Interpreter
from .exceptions import SnarfQuit
from . import utils

class Repl(Interpreter):

    def __init__(self, *args, **kws):
        self.input_handler = kws.pop('input_handler', get_input)
        super().__init__(*args, **kws)

    def get_input(self, prompt='> '):
        return self.input_handler(prompt, history=self.history).strip()

    def repl(self, print_all=False, history='~/.snagit_history'):
        if history:
            self.history = FileHistory(utils.absolute_filename(history))
        else:
            self.history = None

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

            try:
                self.execute(line)
            except SnarfQuit:
                break
            finally:
                if print_all:
                    print(str(self.contents))

        return self.contents
