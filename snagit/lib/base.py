import requests
from urllib3.exceptions import HTTPError

from .. import utils
from ..exceptions import SnarfQuit


class DataProxy:

    def __init__(self, data):
        self._data = data.decode() if isinstance(data, bytes) else data

    def __str__(self):
        return self._data

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __getattr__(self, attr):
        return getattr(self._data, attr)

    @classmethod
    def merge(cls, all_data):
        return cls('\n'.join(str(data) for data in all_data))


class Library:

    def __init__(self):
        self.registry = {}

    def register(self, kind):
        def register(func):
            func.kind = kind
            name = func.__name__.rstrip('_')
            self.registry[name] = func
            return func
        return register


library = Library()
interpreter_library = Library()
register = interpreter_library.register('Program')


@register
def list_(interp, args, kws):
    '''
    List all lines of source code if not empty.
    '''
    linenos = kws.get('linenos', False)
    print('\n'.join(
        '{}{}'.format(i.lineno + ' ' if linenos else '', str(i))
        for i in interp.instructions[:-1]
    ))


@register
def quit(interp, args, kws):
    raise SnarfQuit('Bye!')


@register
def help(interp, args, kws):
    '''
    Display help on available commands.
    '''
    cmds = list(library.registry.items())
    cmds.extend(list(interpreter_library.registry.items()))
    cmds = sorted(cmds)
    format = '    {} ({})'.format
    if not args:
        print('Commands:')
        print('\n'.join(format(name, fn.kind) for name, fn in cmds))
    else:
        cmds = {name: fn for name, fn in cmds}
        for name in args:
            if name in cmds:
                fn = cmds[name]
                print(format(name, fn.kind))
                print(fn.__doc__ if fn.__doc__ else '')
            else:
                print('Unknown command {}'.format(name))


@register
def merge(interp, args, kws):
    '''
    Combine all contents into a single content.
    '''
    interp.contents.merge()


@register
def cache(interp, args, kws):
    '''
    Control caching. Optional arguement of True or False. Defaults to True.
    '''
    interp.loader.use_cache = args[0] if args else True


@register
def load(interp, args, kws):
    '''
    Load new resource(s).
    '''
    range_set = kws.get('range_set', kws.get('range'))
    sources = utils.expand_range_set(args, range_set)
    try:
        contents = interp.load_sources(sources)
    except (requests.RequestException, HTTPError) as exc:
        print('ERROR: {}'.format(exc))


@register
def load_all(interp, args, kws):
    '''
    Load new resource(s) from current content contents array.
    '''
    sources = []
    for content in interp.contents:
        sources.append(str(content))

    load(interp, sources, kws)


@register
def debug(interp, args, kws):
    '''
    Enable a debugging breakpoint.
    '''
    interp.do_debug = True


@register
def parse_line(interp, args, kws):
    print('ARGS >>> {}\nKWDS >>> {}'.format(args, kws))


@register
def run(interp, args, kws):
    for arg in args:
        code = utils.read_file(arg)
        interp.execute(code)


@register
def write(interp, args, kws):
    '''
    Dumps the text representation of all content to the specified file.
    '''
    utils.write_file(args[0], str(interp.contents))


@register
def print_(interp, args, kws):
    '''
    Print out the text representation of the content.
    '''
    print(str(interp.contents))


@register
def end(interp, args, kws):
    interp.contents.pop()
