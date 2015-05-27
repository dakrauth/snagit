import os
import re
import sys
import json
import inspect
import functools
import traceback
from pprint import pformat
from . import utils
from . import snarf

verbose = utils.verbose
set_trace = utils.pdb.set_trace
post_mortem = utils.pdb.post_mortem

#-------------------------------------------------------------------------------
def escaped(txt):
    for cin, cout in (
        ('\\n', '\n'),
        ('\\t', '\t')
    ):
        txt = txt.replace(cin, cout)
    return txt

#-------------------------------------------------------------------------------
def get_doc(method, indent='    '):
    doc = method.__doc__
    return '' if not doc else '\n'.join([
        '{}{}'.format(indent, line.strip())
        for line in doc.splitlines()
    ])


#===============================================================================
class Instruction(object):
    '''
    ``Instruction``'s take the form::
    
        command [arg [arg ...]] [key=arg [key=arg ...]]
        
    Where ``arg`` can be one of: single quoted string, double quoted string,
    digit, True, False, None, or a simple, unquoted string.
    '''
    values_pat = r'''
        r?'(?:(\'|[^'])*?)'   |
        r?"(?:(\"|[^"])*?)"   |
        (\d+)                 |
        (True|False|None)     |
        ([\S]+)
    '''

    args_re = re.compile(r'^((?P<kwd>\w+)=(?P<val>%s)|(?P<arg>%s))\s*' % (values_pat, values_pat), re.VERBOSE)
    value_dict = {'True': True, 'False': False, 'None': None}
    
    #---------------------------------------------------------------------------
    def __repr__(self):
        return '<Instruction({}): {}, {}>'.format(self.cmd, self.args, self.kws)
    
    #---------------------------------------------------------------------------
    def __init__(self, program, line, lineno):
        self.args = []
        self.kws = {}
        self.lineno = lineno
        
        bits = line.split(' ', 1)
        self.cmd = bits[0]
        if len(bits) > 1:
            self.parse(bits[1])
        
    #----------------------------------------------------------------------------
    def get_value(self, s):
        if s.isdigit():
            return int(s)
        elif s in self.value_dict:
            return self.value_dict[s]
        elif s.startswith(('r"', "r'")):
            return re.compile(escaped(s[2:-1]))
        elif s.startswith(('"', "'")):
            return escaped(s[1:-1])
        else:
            return s.strip()

    #---------------------------------------------------------------------------
    def parse(self, text):
        while text:
            m = self.args_re.search(text)
            if not m:
                break
            
            gdict = m.groupdict()
            kwd = gdict.get('kwd')
            if kwd:
                self.kws[kwd] = self.get_value(gdict.get('val', ''))
            else:
                self.args.append(self.get_value(gdict.get('arg', '')))

            text = text[len(m.group()):]
        
        if text:
            raise SyntaxError('Syntax error: "{}" (line {})'.format(text, self.lineno))


#===============================================================================
class Script(object):
    '''
    ``Script`` takes the script source code, scans it, and compiles it into
    ``Instructions``
    '''
    
    #---------------------------------------------------------------------------
    def __init__(self, code=''):
        self.lineno = 1
        self.code = ''
        self.lines = []
        self.instructions = []
        if code:
            self.compile(code)
    
    #---------------------------------------------------------------------------
    def listing(self):
        return [line for line in self.code.splitlines() if line]
        
    #---------------------------------------------------------------------------
    def compile(self, code):
        self.code += '\n' + code if self.code else code
        
        lines = self.scan(code)
        self.lines += lines
        
        instructions = self.parse(lines)
        self.instructions += instructions
        
        return instructions
    
    #----------------------------------------------------------------------------
    def scan(self, text):
        lines = []
        for line in text.splitlines():
            line = line.rstrip()
            if not line or line.lstrip().startswith('#'):
                continue
            lines.append((line, self.lineno))
            self.lineno += 1
            
        verbose('Scanned {} lines from {} bytes', len(lines), len(text))
        return lines

    #---------------------------------------------------------------------------
    def parse_instruction(self, line, lineno):
        bits = line.split(' ', 1)
        cmd = bits.pop(0)
        if bits:
            args, kws, remnants = self.parse_command_inputs(bits[1])
            if remnants:
                verbose('Line {} input remnant: {}', lineno, remnants)
            return (cmd, args, kws, lineno)
        return (cmd, (), {}, lineno)

    #---------------------------------------------------------------------------
    def parse(self, lines):
        return [Instruction(self, l, n) for l, n in lines]


#===============================================================================
class ProgramWarning(Exception):
    '''A program warning occurred.'''


#===============================================================================
class ProgramError(Exception):
    '''A program error occurred.'''


#-------------------------------------------------------------------------------
def register_handler(kind):
    '''
    Create a decorator for the given ``Bits``-derived content handler.
    '''
    def decorator(method):
        method.kind = kind
        method.takes_content = 'content' in inspect.getargspec(method).args
        return method
    return decorator


html_handler = register_handler('Soup')
text_handler = register_handler('Text')
line_handler = register_handler('Lines')


#===============================================================================
class Contents(object):
    
    #---------------------------------------------------------------------------
    def __init__(self, contents=None):
        self.set(contents)
    
    #---------------------------------------------------------------------------
    def __iter__(self):
        return iter(self.contents)
    
    #---------------------------------------------------------------------------
    def __len__(self):
        return len(self.contents)
    
    #---------------------------------------------------------------------------
    def __unicode__(self):
        return '\n'.join([unicode(c) for c in self])
    
    #---------------------------------------------------------------------------
    def __getitem__(self, index):
        return self.contents[index]
    
    #---------------------------------------------------------------------------
    def end(self):
        for content in self:
            content.end()
        
    #---------------------------------------------------------------------------
    def set(self, contents):
        self.contents = []
        if contents:
            if utils.is_string(contents):
                contents = [contents]
            
            for content in contents:
                if not isinstance(content, snarf.Content):
                    if utils.is_string(content):
                        c = content.strip()
                        if c.startswith('<') and c.endswith('>'):
                            content = snarf.BeautifulSoup(content)
                    
                self.contents.append(snarf.Content(content))


#===============================================================================
class Program(object):
    
    #---------------------------------------------------------------------------
    def __init__(self, code='', contents=None, loader=None, use_cache=False, do_pm=False):
        self.loader = loader if loader else utils.Loader(use_cache)
        self.contents = Contents(contents)
        self.do_break = False
        self.do_pm = do_pm
        self.script = Script(code)
        
    #---------------------------------------------------------------------------
    def _get_command(self, cmd):
        return getattr(self, 'cmd_' + cmd, None)
        
    #---------------------------------------------------------------------------
    def repl(self):
        self.loader.load_history()
        print 'Type "help" for more information. Ctrl+c to exit'
        while True:
            try:
                line = raw_input('> ').strip()
            except (EOFError, KeyboardInterrupt):
                break
            
            if not line:
                continue
            
            if line.startswith('!'):
                line = line[1:].strip()
                set_trace()
            if line.startswith('?'):
                line = 'help ' + line[1:]
                
            instrs = self.script.compile(line)
            try:
                self.execute(instrs)
            except ProgramWarning as why:
                print why
        print
        return self.contents
    
    #---------------------------------------------------------------------------
    def _get_commands(self, subset=None):
        cmds = []
        for s in dir(self):
            if s.startswith('cmd_'):
                cmd = s[4:]
                if subset is None or '*' in subset or cmd in subset:
                    cmds.append((cmd, s, getattr(self, s)))

        return cmds
    
    #---------------------------------------------------------------------------
    def _exec(self, instr):
        verbose('Executing {}', instr.cmd)
        method = self._get_command(instr.cmd)
        if method is None:
            raise ProgramWarning('Unknown script instr (line {}): {}'.format(
                instr.lineno,
                instr.cmd
            ))
        
        do_break, self.do_break = self.do_break, False
        error = None
        try:
            if do_break: set_trace()
            if getattr(method, 'takes_content', False):
                for content in self.contents:
                     method(content, instr.args, instr.kws)
            else:
                method(instr.args, instr.kws)
        except:
            exc, value, tb = sys.exc_info()
            if self.do_pm:
                utils.logger.error('Script exception, line {}: {}'.format(instr.lineno, value))
                utils.logger.error('{0} Entering post_mortem {0}'.format('*' * 8))
                post_mortem(tb)
            else:
                print traceback.print_exc()
            raise ProgramError('Line {}: {}'.format(instr.lineno, value))
    
    #---------------------------------------------------------------------------
    def execute(self, instructions=None):
        instructions = instructions or self.script.instructions
        for instr in instructions:
            self._exec(instr)
        
        return self.contents
    
    #---------------------------------------------------------------------------
    def cmd_list(self, args, kws):
        '''
        List all lines of source code if not empty.
        '''
        print '\n'.join(self.script.listing())
    
    #---------------------------------------------------------------------------
    def cmd_help(self, args, kws):
        '''
        Display help on available commands.
        '''
        if not args:
            print 'Commands:'
            print '\n'.join(['    ' + s[0] for s in self._get_commands()])
        else:
            cmds = self._get_commands(args)
            for cmd, method_name, method in cmds:
                docstr = get_doc(method)
                if getattr(method, 'takes_content', False):
                    cmd += ' - ({} content)'.format(method.kind)
                print cmd
                if docstr:
                    print docstr
    
    #---------------------------------------------------------------------------
    def cmd_combine(self, args, kws):
        '''
        Combine all contents into a single content.
        '''
        if len(self.contents) > 1:
            self.contents.set(snarf.Content.combine(self.contents))
    
    #---------------------------------------------------------------------------
    def cmd_serialize(self, args, kws):
        '''
        Serialize content data into either 'python' or 'json'.
        '''
        self.cmd_combine((), {})
        content = self.contents[0]
        content.serialize(**kws)
    
    #---------------------------------------------------------------------------
    def cmd_cache(self, args, kws):
        '''
        Enable caching.
        '''
        self.loader.use_cache()
    
    #---------------------------------------------------------------------------
    def cmd_load(self, args, kws):
        '''
        Load new resource(s).
        '''
        contents = self.loader.load(args, **kws)
        self.contents.set(contents)
    
    #---------------------------------------------------------------------------
    def cmd_load_all(self, args, kws):
        '''
        Load new resource(s) from current content contents array.
        '''
        sources = []
        for content in self.contents:
            sources.extend(list(content))
        
        self.cmd_load(sources, kws)
    
    #---------------------------------------------------------------------------
    def cmd_break(self, args, kws):
        '''
        Enable a debugging breakpoint.
        '''
        self.do_break = True
    
    #---------------------------------------------------------------------------
    def cmd_echo(self, args, kws):
        verbose('>>> {}', args)
    
    #---------------------------------------------------------------------------
    def cmd_write(self, args, kws):
        '''
        Dumps the text representation of all content to the specified file.
        '''
        data = '\n'.join([unicode(c) for c in self.contents])
        utils.write_file(args[0], data)

    #---------------------------------------------------------------------------
    def cmd_dumps(self, args, kws):
        '''
        Print out the text representation of the content.
        '''
        print unicode(self.contents)
    
    #---------------------------------------------------------------------------
    def cmd_end(self, args, kws):
        self.contents.end()

    #---------------------------------------------------------------------------
    # Lines methods
    #---------------------------------------------------------------------------

    #---------------------------------------------------------------------------
    @line_handler
    def cmd_skip_to(self, content, args, kws):
        '''
        Skip lines until finding a matching line.
        '''
        content.skip_to(args[0], **kws)
    
    #---------------------------------------------------------------------------
    @line_handler
    def cmd_read_until(self, content, args, kws):
        '''
        Save lines until finding a matching line.
        '''
        content.read_until(args[0], **kws)

    #---------------------------------------------------------------------------
    @line_handler
    def cmd_strip(self, content, args, kws):
        '''
        Strip whitespace from content.
        '''
        content.strip()
    
    #---------------------------------------------------------------------------
    @line_handler
    def cmd_matches(self, content, args, kws):
        '''
        Save lines matching the input.
        '''
        content.matches(args[0], **kws)
    
    #---------------------------------------------------------------------------
    @line_handler
    def cmd_compress(self, content, args, kws):
        '''
        Strip, split, and rejoin each line using a single space.
        '''
        content.compress()

    #---------------------------------------------------------------------------
    @line_handler
    def cmd_format(self, content, args, kws):
        '''
        Format each line, where the current line is passed using {}.
        '''
        content.format(args[0])
    
    #---------------------------------------------------------------------------
    # Text methods
    #---------------------------------------------------------------------------

    #---------------------------------------------------------------------------
    @text_handler
    def cmd_remove(self, content, args, kws):
        '''
        Remove each string argument from the text.
        '''
        content.remove_each(args, **kws)
    
    #---------------------------------------------------------------------------
    @text_handler
    def cmd_replace(self, content, args, kws):
        '''
        Replace each string argument with the last given argument as the replacement.
        '''
        args = args[:]
        replacement = args.pop()
        args = [(a, replacement) for a in args]
        content.replace_each(args, **kws)
    
    #---------------------------------------------------------------------------
    # HTML methods
    #---------------------------------------------------------------------------

    #---------------------------------------------------------------------------
    @html_handler
    def cmd_remove_attrs(self, text, args, kws):
        '''
        Removes the specified attributes from all elements.
        '''
        text.remove_attrs(args[0] if args else None, **kws)
    
    #---------------------------------------------------------------------------
    @html_handler
    def cmd_unwrap(self, content, args, kws):
        '''
        Replace an element with its child contents.
        '''
        for tag in args:
            content.unwrap(tag, **kws)

    #---------------------------------------------------------------------------
    @html_handler
    def cmd_extract(self, content, args, kws):
        '''
        Removes the specified elements.
        '''
        for tag in args:
            content.extract(tag, **kws)
    
    #---------------------------------------------------------------------------
    @html_handler
    def cmd_select(self, content, args, kws):
        '''
        Whittle down elements to those matching the CSS selection.
        '''
        content.select(args[0])

    #---------------------------------------------------------------------------
    @html_handler
    def cmd_select_attr(self, content, args, kws):
        '''
        Using the given CSS selector, pull out the specified attribute text into Lines.
        '''
        content.select_attr(args[0], args[1])
        
    #---------------------------------------------------------------------------
    @html_handler
    def cmd_replace_tag(self, content, args, kws):
        '''
        Replace the specified tag with some plain text.
        '''
        content.replace_with(args[0], args[1])
    
    #---------------------------------------------------------------------------
    @html_handler
    def cmd_collapse(self, content, args, kws):
        '''
        Given a CSS selector, combine multiple whitespace chars into a single space and trim.
        '''
        for arg in args:
            content.collapse(arg, **kws)


#-------------------------------------------------------------------------------
def execute_script(filename, contents):
    code = utils.read_file(filename)
    scr = Program(code, contents)
    return scr.execute()
