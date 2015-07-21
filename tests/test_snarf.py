import re
import shutil
from os.path import join, dirname, exists
import sys
import unittest
from snarf.snarf import Contents, BeautifulSoup
from snarf import script
from snarf import utils
from snarf.loader import Loader
try:
    import ipdb as pdb
except ImportError:
    import pdb


R = re.compile

THIS_DIR = dirname(__file__)
FIXTURES_DIR = join(THIS_DIR, 'fixtures')
DATA_DIR = join(FIXTURES_DIR, 'data')

#-------------------------------------------------------------------------------
def read_test_data(basename):
    return utils.read_file(join(DATA_DIR, basename))


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
    def _do_instruction(self, line, expect_cmd, expect_args=None, expect_kws=None):
        expect_args = expect_args or ()
        expect_kws = expect_kws or {}
        prog = script.Script(line)
        inst = prog.instructions[0]

        self.assertEqual(inst.cmd, expect_cmd)
        self.assertEqual(len(inst.args), len(expect_args))
        for actual, expect in zip(inst.args, expect_args):
            if utils.is_regex(expect):
                self.assertEqual(expect.pattern, actual.pattern)
            else:
                self.assertEqual(actual, expect)
            
        self.assertDictEqual(inst.kws, expect_kws)

    #---------------------------------------------------------------------------
    def test_parse_instruction(self):
        self._do_instruction("foo bar 'baz spam'", 'foo', ['bar', 'baz spam'], {})
        self._do_instruction("x r'[abc]'", 'x', [R('[abc]')], {})
        self._do_instruction("z foo=bar baz 'foo'", 'z', ['baz', 'foo'], {'foo': 'bar'})
        
        self._do_instruction(
            """replace r'a+b' x='a b c' y=23 z=True baz=r'spam+'""",
            'replace',
            [R('a+b')],
            {'x': 'a b c', 'y': 23, 'z': True, 'baz': R('spam+')}
        )

        self._do_instruction(
            """commandx _=34 __=None""",
            'commandx',
            expect_kws={'_': 34, '__': None}
        )
        
        self._do_instruction(
            """command abc7 'True' _ _=34 __=None""",
            'command',
            ['abc7', 'True', '_'],
            {'_': 34, '__': None}
        )


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


#===============================================================================
class TestLoader(unittest.TestCase):
    
    #---------------------------------------------------------------------------
    def setUp(self):
        self.snarf_dir = join(THIS_DIR, 'cache')
    
    #---------------------------------------------------------------------------
    def tearDown(self):
        if exists(self.snarf_dir):
            # probably overly excessive sanity here
            start = os.path.expanduser('~')
            if self.snarf_dir.startswith(start):
                shutil.rmtree(self.snarf_dir)
            else:
                print 'Unable to remove cache directory "{}"'.format(self.snarf_dir)
        
    #---------------------------------------------------------------------------
    def test_cache_dir_creation(self):
        loader = Loader(use_cache=True, cache_base=self.snarf_dir)
        self.assertEqual(loader.cache_dir, join(self.snarf_dir, 'snarf', 'cache'))
        self.assertTrue(exists(loader.cache_dir))


################################################################################
if __name__ == '__main__':
    unittest.main()
