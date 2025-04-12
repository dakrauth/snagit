from pathlib import Path

from . import DataProxy
from .. import utils
from ..core import BaseLibrary
from ..exceptions import SnagitStopInteration


class Library(BaseLibrary):
    name = "prog"

    def prog_parser(self, data, args, kwargs):
        """
        Speicify the BeautifulSoup parser to use.
        """
        utils.config.parser = args[0]

    def prog_merge(self, data, args, kwargs):
        """
        Combine all contents into a single content.
        """
        self.interpreter.contents.merge()
        raise SnagitStopInteration("merged")

    def prog_cache(self, data, args, kwargs):
        """
        Control caching.

        Optional argument of True or False (defaults to True). Use no, false, or 0 to negate.
        """
        arg = True
        if args:
            arg = False if args[0].lower() in {"0", "false", "no", "n"} else True

        self.interpreter.loader.use_cache = arg

    def _load(self, args, kwargs):
        range_set = kwargs.get("range_set", kwargs.get("range"))
        sources = utils.expand_range_set(args, range_set)
        results = []
        for src in sources:
            content = self.interpreter.load_source(src)
            results.append(DataProxy(content))

        return results

    def prog_load(self, data, args, kwargs):
        """
        Load new resource(s).
        """
        results = self._load(args, kwargs)
        self.interpreter.contents.update(results)
        raise SnagitStopInteration("load complete")

    def prog_load_all(self, data, args, kwargs):
        """
        Load new resource(s) from current content contents array.
        """
        results = []
        for content in self.interpreter.contents:
            results.extend(self._load([str(content)], {}))

        self.interpreter.contents.update(results)
        raise SnagitStopInteration("load all complete")

    def prog_debug(self, data, args, kwargs):
        """
        Enable a debugging breakpoint.
        """
        self.interpreter.do_debug = True

    def prog_run(self, data, args, kwargs):
        for arg in args:
            code = Path(arg).read_text()
            self.interpreter.execute(code)

    def prog_write(self, data, args, kwargs):
        """
        Dumps the text representation of all content to the specified file.
        """
        Path(args[0]).write_text(str(self.interpreter.contents))

    def prog_print(self, data, args, kwargs):
        """
        Print out the text representation of the content.
        """
        if args:
            print(" ".join(str(s) for s in args))
        print(str(self.interpreter.contents))

    def prog_end(self, data, args, kwargs):
        self.interpreter.contents.pop()

    def prog_struct(self, data, args, kwargs):
        self.interpreter.contents.struct(
            args, strip=kwargs.get("strip", False), name=kwargs.get("name")
        )

    def prog_help(self, data, args, kwargs):
        """
        Display help on available commands.
        """
        registry = self.interpreter.registry
        if not args:
            seen = set()
            items = []
            for fn in registry.values():
                info = fn.snagit
                if info.long_name in seen:
                    continue

                seen.add(info.long_name)
                items.append((info.short_name, f"{info.short_descr} ({info.long_name})"))

            mx = max(len(key) for key, value in items) + 4
            listing = "\n".join(f"    {name:.<{mx}}{descr}" for name, descr in sorted(items))
            print(f"Commands:\n{listing}")
            # import ipdb; ipdb.set_trace()

            return

        lines = []
        for name in args:
            if name in registry:
                info = registry[name].snagit
                lines.append(f"{info.long_name} ({info.short_name})")
                if info.short_descr:
                    lines.append(f"    {info.short_descr}\n")
                if info.long_descr:
                    lines.append(
                        "\n".join(f"    {line.strip()}" for line in info.long_descr.splitlines()),
                        end="\n\n",
                    )

            else:
                lines.append("Unknown command {}".format(name))

        print("\n".join(lines))
