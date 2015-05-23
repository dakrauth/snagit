import re
import sys
import traceback
from .snarf import Lines, Text
from . import script
try:
    import ipdb as pdb
except ImportError:
    import pdb

#-------------------------------------------------------------------------------
def test_simple():
    if pdb:
        pdb.set_trace()
        
    lines = Lines('''foo bar baz\nspam     \nxxxxxxxx\nzzzz\n   \t   123\n   u6ejtryn\n456''')
    func = re.compile('[123]').search
    lines.compress().skip_to(func, False).read_until('456', False)
    text = lines.text
    print text, text == 'u6ejtryn'
    
    text = lines.end().text
    print text, text == '456'
    return True


#-------------------------------------------------------------------------------
def val_repr(val):
    if hasattr(val, 'pattern'):
        return '/{}/'.format(val.pattern)
    
    if isinstance(val, basestring):
        return repr(val)
        
    return val
    
#-------------------------------------------------------------------------------
def test_instr():
    lines = (
        "foo bar 'baz spam'",
        "x r'[abc]'",
        "z foo=bar baz 'bob'",
        """replace r'a+b' x='a b c' y=23 z=True baz=r'spam+'""",
    )
    for line in lines:
        print '-' * 79
        prog = script.Program(line)
        print line
        ins = prog.instructions[0]
        print ins.cmd, ins.lineno

        for i, arg in enumerate(ins.args):
            print 'Arg %3d: %s' % (i, val_repr(arg))

        for kwd in ins.kws:
            print '%7s: %s' % (kwd, val_repr(ins.kws[kwd]))

    print '-' * 79
    return True


#-------------------------------------------------------------------------------
def main():
    ns = globals()
    args = sys.argv[1:]
    if not args:
        args = [k.replace('test_', '', 1) for k in ns if k.startswith('test_')]
        
    for arg in args:
        tfn = 'test_' + arg
        func = ns.get(tfn)
        if not func:
            print 'Unknown test function {}'.format(tfn)
        else:
            try:
                result = func()
            except Exception as why:
                print '*** Function {} exception: {}'.format(tfn, why)
                traceback.print_exc()
            else:
                print '{} {}'.format('+++' if result else '---', tfn)


#===============================================================================
if __name__ == '__main__':
    main()