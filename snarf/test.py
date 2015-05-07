import re
from .snarf import Lines, Text
try:
    import ipdb as pdb
except ImportError:
    import pdb

def test(pdb=False):
    if pdb:
        pdb.set_trace()
        
    lines = Lines('''foo bar baz
spam     
xxxxxxxx
zzzz
   \t   123
   u6ejtryn
456''')
    
    func = re.compile('[123]').search
    lines.compress().skip_to(func, False).read_until('456', False)
    text = lines.text
    print text, text == 'u6ejtryn'
    
    text = lines.end().text
    print text, text == '456'

