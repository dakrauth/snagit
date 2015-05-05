import re
from .snarf import Lines

################################################################################
if __name__ == '__main__':
    lines = Lines('''foo bar baz
spam     
xxxxxxxx
zzzz
   \t   123
   u6ejtryn
456''')
    
    #import ipdb; ipdb.set_trace()
    func = re.compile('[123]').search
    lines.compress().skip_to(func, False).read_until('456', False)
    text = lines.text
    print text, text == 'u6ejtryn'
    
    text = lines.end().text
    print text, text == '456'

