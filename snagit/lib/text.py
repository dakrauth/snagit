# -*- coding:utf8 -*-
import logging
import strutil

from . import DataProxy, library

logger = logging.getLogger(__name__)
register = library.register('Text')


@register
def remove_each(data, args, kws):
    data = str(data)
    for arg in args:
        data = strutil.remove_each(data, arg, **kws)

    return DataProxy(data)


@register
def replace_each(data, args, kws):
    '''
    Use arg[0] as a replacement for all args[1:]
    '''
    replacement = args[0]
    data = strutil.replace_each(
        str(data),
        [(arg, replacement) for arg in args[1:]],
        **kws
    )

    return DataProxy(data)


@register
def compress_text(data, args, kws):
    lines = str(data).splitlines()
    return DataProxy('\n'.join(' '.join(
        l.strip() for l in line.split()) for line in lines if line.strip()
    ))
