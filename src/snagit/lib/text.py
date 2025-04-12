import logging

from . import DataProxy
from .. import utils
from ..core import BaseLibrary

logger = logging.getLogger(__name__)


class Library(BaseLibrary):
    name = "text"

    def text_remove(self, data, args, kwargs):
        """
        Remove the givens strings from the text content.
        """
        data = str(data)
        for arg in args:
            data = utils.remove_each(data, arg, **kwargs)

        return DataProxy(data)

    def text_replace(self, data, args, kwargs):
        """
        Use arg[0] as a replacement for all args[1]
        """
        data = utils.replace(
            str(data),
            new=args[0],
            old=args[1],
            count=int(kwargs["count"]) if "count" in kwargs else None,
            strip=kwargs.get("strip", False),
        )

        return DataProxy(data)

    def text_compress(self, data, args, kwargs):
        """
        Compress runs of multiple whitespace characters.
        """
        lines = str(data).splitlines()
        return DataProxy(
            "\n".join(
                " ".join(word.strip() for word in line.split()) for line in lines if line.strip()
            )
        )
