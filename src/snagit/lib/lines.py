import logging

from . import DataProxy
from .. import utils
from ..core import BaseLibrary

logger = logging.getLogger(__name__)


def is_lines(what):
    return isinstance(what, (list, tuple))


def _prepare_lines(data):
    if is_lines(data):
        return list(data)
    elif isinstance(data, Lines):
        return data._data[:]

    return str(data).splitlines()


class Lines(DataProxy):
    """
    Handler class for manipulating and traversing lines of text.
    """

    def __init__(self, data):
        super().__init__(_prepare_lines(data))

    def __str__(self):
        return "\n".join(self._data)

    @classmethod
    def merge(cls, all_data):
        data = []
        for lines in all_data:
            data += lines._data

        return cls(data)


class Library(BaseLibrary):
    name = "lines"

    def lines_format(self, data, args, kws):
        """
        Format each line.

        The current line is passed using {}.
        """
        fmt = args[0]
        return Lines(
            [fmt.format(line, lineno) for lineno, line in enumerate(_prepare_lines(data), 1)]
        )

    def lines_strip(self, data, args, kws):
        """
        Strip whitespace from content.
        """
        return Lines([ln.strip() for ln in _prepare_lines(data)])

    def lines_lines(self, data, args, kws):
        """
        Convert current content into lines of text.
        """
        return Lines(data)

    def lines_skip_to(self, data, args, kws):
        """
        Skip lines until finding a matching line.
        """
        lines = _prepare_lines(data)
        keep = kws.pop("keep", False)
        found = utils.find_first(lines, str(args[0]))
        if found is not None:
            if not keep:
                found += 1

            lines = lines[found:]

        return Lines(lines)

    def lines_read_until(self, data, args, kws):
        """
        Save lines until finding a matching line.
        """
        keep = kws.pop("keep", False)
        lines = _prepare_lines(data)
        found = utils.find_first(lines, str(args[0]))
        if found is not None:
            if keep:
                found += 1

            lines = lines[:found]

        return Lines(lines)

    def lines_matches(self, data, args, kws):
        """
        Save lines matching the input.
        """
        return Lines([ln for ln in _prepare_lines(data) if utils.matches(ln, args[0])])
