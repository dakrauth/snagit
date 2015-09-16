import os

def loader_sanity():
    from snarf import utils
    from snarf import loader
    utils.enable_debug_logger()
    l = loader.Loader(True, './test-cache')
    l.load_source('http://httpbin.org/links/10/0')


def format_sanity():
    from snarf import markup
    from snarf.core import make_soup
    p = make_soup(
        '<p>Hello, <br>Break<br>HR <img src="asdf">Image <input type="text">Input</p>',
        'html5lib'
    )
    print p.prettify()
    print '-' * 40
    print markup.format(p)


if __name__ == '__main__':
    format_sanity()