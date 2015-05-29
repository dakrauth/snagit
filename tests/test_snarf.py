import re
from os.path import join, dirname
import sys
import unittest
from snarf.snarf import Content, BeautifulSoup
from snarf import script
from snarf import utils
try:
    import ipdb as pdb
except ImportError:
    import pdb


R = re.compile
#-------------------------------------------------------------------------------

def read_data(basename):
    return utils.read_file(join(dirname(__file__), 'data', basename))


#-------------------------------------------------------------------------------
def display(what):
    print '~' * 60
    print what
    print '~' * 60


#===============================================================================
class TestLines(object):

    #---------------------------------------------------------------------------
    def test_simple(self):
        data = read_data('lines.txt')
        lines = Content(data.splitlines())
        lines.compress()
        assert unicode(lines) == '''foo bar baz\nspam\nxxxxxxxx\nzzzz\n123\nu6ejtryn\n456'''
    
        lines.skip_to('123', False)
        assert unicode(lines) == 'u6ejtryn\n456'
    
        lines.read_until('456', False)
        assert unicode(lines) == u'u6ejtryn'
    
        lines.end()
        assert unicode(lines) == u'u6ejtryn\n456'


#===============================================================================
class TestInstructions(object):

    #---------------------------------------------------------------------------
    def _do_instruction(self, line, expect):
        cmd, args, kws = expect
        prog = script.Script(line)
        inst = prog.instructions[0]

        assert inst.cmd == cmd
        for actual, expect in zip(inst.args, args):
            if utils.is_regex(expect):
                assert expect.pattern == actual.pattern
            else:
                assert actual == expect
            
        assert inst.kws == kws

    #---------------------------------------------------------------------------
    def test_instruction1(self):
        self._do_instruction("foo bar 'baz spam'", ('foo', ['bar', 'baz spam'], {}))

    #---------------------------------------------------------------------------
    def test_instruction2(self):
        self._do_instruction("x r'[abc]'", ('x', [R('[abc]')], {}))

    #---------------------------------------------------------------------------
    def test_instruction3(self):
        self._do_instruction("z foo=bar baz 'foo'", (
            'z',
            ['baz', 'foo'],
            {'foo': 'bar'}
        ))

    #---------------------------------------------------------------------------
    def test_instruction4(self):
        self._do_instruction("""replace r'a+b' x='a b c' y=23 z=True baz=r'spam+'""", (
            'replace',
            [R('a+b')],
            {'x': 'a b c', 'y': 23, 'z': True, 'baz': R('spam+')}
        ))

    #---------------------------------------------------------------------------
    def test_instruction5(self):
        self._do_instruction("""commandx _=34 __=None""", (
            'commandx',
            [],
            {'_': 34, '__': None}
        ))

    #---------------------------------------------------------------------------
    def test_instruction6(self):
        self._do_instruction("""command abc7 'True' _ _=34 __=None""", (
            'command',
            ['abc7', 'True', '_'],
            {'_': 34, '__': None}
        ))


#===============================================================================
class TestHTML(unittest.TestCase):
    
    EXPECTED_HTML = '''<html>
<head>
    <title>Links</title>
</head>
<body>
    0
    <a href="/links/10/1">1</a>
    <a href="/links/10/2">2</a>
    <a href="/links/10/3">3</a>
    <a href="/links/10/4">4</a>
    <a href="/links/10/5">5</a>
    <a href="/links/10/6">6</a>
    <a href="/links/10/7">7</a>
    <a href="/links/10/8">8</a>
    <a href="/links/10/9">9</a>
</body>
</html>'''
    
    #---------------------------------------------------------------------------
    def setUp(self):
        self.data = utils.read_url('http://httpbin.org/links/10/0')
    
    #---------------------------------------------------------------------------
    def test_select_attr(self):
        h = Content(BeautifulSoup(self.data))
        h.select_attr('a', 'href')
        assert h.lines == ['/links/10/{}'.format(i) for i in range(1,10)]

    #---------------------------------------------------------------------------
    def test_dumps(self):
        h = Content(BeautifulSoup(self.data))
        #pdb.set_trace()
        assert unicode(h) == self.EXPECTED_HTML


################################################################################
if __name__ == '__main__':
    unittest.main()
