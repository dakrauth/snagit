from ..core import BaseLibrary
from ..exceptions import SnagitQuit


class Library(BaseLibrary):
    name = "repl"

    def repl_list(self, data, args, kwargs):
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

    def repl_quit(self, data, args, kwargs):
        """
        Exit the program
        """
        raise SnagitQuit("Bye!")

    def repl_parse_line(self, data, args, kwargs):
        print("ARGS >>> {}\nKWDS >>> {}".format(args, kwargs))
