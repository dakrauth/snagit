import re
from os.path import join, dirname
import sys
import unittest
from snarf.snarf import Contents, BeautifulSoup
from snarf import script
from snarf import utils
try:
    import ipdb as pdb
except ImportError:
    import pdb


R = re.compile

#-------------------------------------------------------------------------------
def read_test_data(basename):
    return utils.read_file(join(dirname(__file__), 'data', basename))


#-------------------------------------------------------------------------------
def display(what):
    print '{0}\n{1}\n{0}'.format('~' * 60, what)


#===============================================================================
class TestLines(unittest.TestCase):

    #---------------------------------------------------------------------------
    def test_simple(self):
        data = read_test_data('lines.txt')
        lines = Contents([data])

        lines.strip()
        text = unicode(lines)
        self.assertMultiLineEqual(text, u'''foo bar baz\nspam\nxxxxxxxx\nzzzz\n123\nu6ejtryn\n456''')
    
        lines.skip_to('123', False)
        text = unicode(lines)
        self.assertMultiLineEqual(text, u'u6ejtryn\n456')
    
        lines.read_until('456', False)
        text = unicode(lines)
        self.assertEqual(text, u'u6ejtryn')
    
        lines.end()
        text = unicode(lines)
        self.assertMultiLineEqual(text, u'u6ejtryn\n456')


#===============================================================================
class TestInstructions(unittest.TestCase):

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
    
    EXPECTED_ATTRS = ['/links/10/{}'.format(i) for i in range(1,10)]
    maxDiff = None
    
    #---------------------------------------------------------------------------
    def setUp(self):
        self.data = read_test_data('httpbin_links.html')
    
    #---------------------------------------------------------------------------
    def test_select_attr(self):
        bs = BeautifulSoup(self.data)
        h = Contents([bs])
        h.select_attr('a', 'href')
        lines = h.data_merge()
        self.assertSequenceEqual(lines, self.EXPECTED_ATTRS)

    #---------------------------------------------------------------------------
    def test_dumps(self):
        bs = BeautifulSoup(self.data)
        h = Contents([bs])
        text = unicode(h)
        self.assertMultiLineEqual(text, read_test_data('expected_httpbin_links.html'))


################################################################################
if __name__ == '__main__':
    unittest.main()
