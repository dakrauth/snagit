from ..core import BaseLibrary
from ..exceptions import SnagitQuit


class Library(BaseLibrary):
    name = "repl"

    @BaseLibrary.alias("l")
    def repl_list(self, args, kwargs):
        """
        List all lines of source code if not empty.
        """
        linenos = kwargs.get("linenos", False)
        print(
            "\n".join(
                "{}{}".format(i.lineno + " " if linenos else "", str(i))
                for i in self.interpreter.instructions[:-1]
            )
        )

    @BaseLibrary.alias("e")
    def repl_echo(self, args, kwargs):
        """
        Toggle the instruction echo feature.
        """
        self.interpreter.do_echo = not self.interpreter.do_echo
        print(f"Echo is now {'on' if self.interpreter.do_echo else 'off'}")

    @BaseLibrary.alias("q")
    def repl_quit(self, args, kwargs):
        """
        Exit the program
        """
        raise SnagitQuit("Bye!")

    def repl_parse_line(self, data, args, kwargs):
        print("ARGS >>> {}\nKWDS >>> {}".format(args, kwargs))
