from prompt_toolkit.shortcuts import get_input
from prompt_toolkit.history import FileHistory

from .core import Interpreter

class Repl(Interpreter):

    def get_input(self, prompt='> '):
        return get_input(prompt, history=self.history).strip()

    def repl(self, print_all=False):
        self.history = FileHistory('.snarf_history')
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

            self.execute(line)
            if print_all:
                print(str(self.contents))

        return self.contents
