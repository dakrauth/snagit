import re
import sys
from snarf.snarf import Lines, Text
from snarf import script
try:
    import ipdb as pdb
except ImportError:
    import pdb


SOME_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title></title>
    <meta name="description" content="">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="" rel="stylesheet" media="all">
    <script src=""></script>
</head>
<body>
    <header role="banner">
        <h1></h1>
        <nav role="navigation"></nav>
    </header>
    <div class="wrap">
        <main role="main" style="li { color: red; }">
            <ul>
                <li class="abc"><a href="/abc/foo1">line 1</a></li>
                <li class="abc"><a href="/abc/foo2">line 2</a></li>
                <li class="efg"><a href="/xyz/foo3">line 3</a></li>
                <li class="efg"><a href="/xyz/foo4">line 4</a></li>
                <li class="abc efg">line 5</li>
                <li class="xyz">line 6</li>
            </ul>
        </main>
    </div>
    <footer role="contentinfo">
        <small>Copyright &copy; <time datetime="2014">2014</time></small>
    </footer>
    <script>
        (function() {

        }());
    </script>
</body>
</html>'''

SOME_LINES = '''foo bar baz
spam     
xxxxxxxx
zzzz
   \t   123
   u6ejtryn
456'''

R = re.compile

#-------------------------------------------------------------------------------
def display(what):
    print '~' * 60
    print what
    print '~' * 60

#-------------------------------------------------------------------------------
def test_simple():
    lines = Lines(SOME_LINES)
    lines.compress()
    display(unicode(lines))
    assert unicode(lines) == '''foo bar baz
spam
xxxxxxxx
zzzz
123
u6ejtryn
456'''
    
    lines.skip_to('123', False)
    display(unicode(lines))
    assert unicode(lines) == 'u6ejtryn\n456'
    
    lines.read_until('456', False)
    display(unicode(lines))
    assert unicode(lines) == u'u6ejtryn'
    
    lines.end()
    display(unicode(lines))
    assert unicode(lines) == u'u6ejtryn\n456'


#-------------------------------------------------------------------------------
def val_repr(val):
    if hasattr(val, 'pattern'):
        return '/{}/'.format(val.pattern)
    
    if isinstance(val, basestring):
        return repr(val)
        
    return val

#-------------------------------------------------------------------------------
def do_instr(line, expect):
    cmd, args, kws = expect
    prog = script.Program(line)
    inst = prog.instructions[0]
    
    assert inst.cmd == cmd
    assert inst.args == args
    assert inst.kws == kws


#-------------------------------------------------------------------------------
def test_instrs1():
    do_instr("foo bar 'baz spam'", ('foo', ['bar', 'baz spam'], {}))


#-------------------------------------------------------------------------------
def test_instrs2():
    do_instr("x r'[abc]'", ('x', [R('[abc]')], {}))


#-------------------------------------------------------------------------------
def test_instrs3():
    do_instr("z foo=bar baz 'foo'", ('z', ['baz', 'foo'], {'foo': 'bar'}))


#-------------------------------------------------------------------------------
def test_instrs4():
    do_instr("""replace r'a+b' x='a b c' y=23 z=True baz=r'spam+'""", (
        'replace',
        [R('a+b')],
        {'x': 'a b c', 'y': 23, 'z': True, 'baz': R('spam+')}
    ))


#-------------------------------------------------------------------------------
def test_instrs5():
    do_instr("""commandx _=34 __=None""", (
        'commandx',
        [],
        {'_': 34, '__': None}
    ))


#-------------------------------------------------------------------------------
def test_instrs6():
    do_instr("""command abc7 'True' _ _=34 __=None""", (
        'command',
        ['abc7', 'True', '_'],
        {'_': 34, '__': None}
    ))

if __name__ == '__main__':
    pdb.set_trace()
    test_instrs6()