import re
import json
from . import utils
from . import snarf

verbose = utils.verbose

#-------------------------------------------------------------------------------
def content_command(method):
    method.takes_content = True
    return method


#===============================================================================
class Instruction(object):
    
    values_pat = r'''(
        r?'(?:(\'|[^'])*?)'   |
        r?"(?:(\"|[^"])*?)"   |
        (\d+)               |
        (True|False|None)
    )\s*'''

    args_re = re.compile(r'^%s' % values_pat, re.VERBOSE)
    kwds_re = re.compile(r'^(\w+)=%s' % values_pat, re.VERBOSE)
    value_dict = {'True': True, 'False': False, 'None': None}
    
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
        elif s.startswith('r'):
            return re.compile(s[2:-1])
        
        return s[1:-1]

    #---------------------------------------------------------------------------
    def parse(self, text):
        while text:
            m = self.args_re.search(text)
            if not m:
                break
        
            self.args.append(self.get_value(m.group(1)))
            text = text[len(m.group()):]
        
        while text:
            m = self.kwds_re.search(text)
            if not m:
                break
            
            self.kws[m.group(1)] = self.get_value(m.group(2))
            text = text[len(m.group()):]
        
        if text:
            raise SyntaxError('Syntax error: "{}" (line {})'.format(text, self.lineno))


#===============================================================================
class Program(object):
    
    
    #---------------------------------------------------------------------------
    def __init__(self):
        self.lineno = 1
        self.code = ''
        self.lines = []
        self.instructions = []

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
class ScriptError(Exception):
    pass


#===============================================================================
class Script(object):
    
    #---------------------------------------------------------------------------
    def __init__(self, code='', contents=None, loader=None, use_cache=False):
        self.loader = loader if loader else utils.Loader()
        if use_cache:
            self.loader.use_cache()
            
        self.set_contents(contents)
        self.do_break = False
        self.program = Program()
        if code:
            self.program.compile(code)
        
    #---------------------------------------------------------------------------
    def set_contents(self, contents):
        if contents:
            if utils.is_string(contents):
                contents = [contents]
                
            self.contents = [snarf.Text(unicode(c)) for c in contents]
        else:
            self.contents = []
    
    #---------------------------------------------------------------------------
    def get_command(self, cmd):
        return getattr(self, 'cmd_' + cmd, None)
        
    #---------------------------------------------------------------------------
    def repl(self):
        print 'Type "help" for more information. Ctrl+c to exit'
        while True:
            try:
                line = raw_input('> ').strip()
            except (EOFError, KeyboardInterrupt):
                break
            
            if not line:
                continue
            
            if line.startswith('?'):
                line = line[1:].strip()
                utils.pdb.set_trace()
            
            instrs = self.program.compile(line)
            try:
                self.execute(instrs)
            except ScriptError as why:
                print why
            
        return self.contents
        
    #---------------------------------------------------------------------------
    def _exec(self, instr):
        verbose('Executing {}', instr.cmd)
        method = self.get_command(instr.cmd)
        if method is None:
            raise ScriptError('Unknown script instr (line {}): {}'.format(
                instr.lineno,
                instr.cmd
            ))
        
        do_break, self.do_break = self.do_break, False
        if getattr(method, 'takes_content', False):
            new_contents = []
            for content in self.contents:
                try:
                    if do_break: utils.pdb.set_trace()
                    new_content = method(content, instr.args, instr.kws)
                except Exception as exc:
                    exc.args += ('Line {}'.format(instr.lineno),)
                    raise
                else:
                    new_contents.append(new_content)
        
            self.contents = new_contents
        else:
            try:
                if do_break: utils.pdb.set_trace()
                method(instr.args, instr.kws)
            except Exception as exc:
                exc.args += ('Line {}'.format(instr.lineno),)
                raise
            
    #---------------------------------------------------------------------------
    def execute(self, instructions=None):
        instructions = instructions or self.program.instructions
        for instr in instructions:
            self._exec(instr)
        
        return self.contents
    
    #---------------------------------------------------------------------------
    def cmd_list(self, args, kws):
        for line in self.program.code.splitlines():
            if line:
                print line
    
    #---------------------------------------------------------------------------
    def cmd_help(self, args, kws):
        print 'Commands:\n{}\n'.format(
            '\n'.join(['   ' + s[4:] for s in dir(self) if s.startswith('cmd_')])
        )
    
    #---------------------------------------------------------------------------
    def cmd_cache(self, args, kws):
        self.loader.use_cache()
    
    #---------------------------------------------------------------------------
    def cmd_load(self, args, kws):
        contents = self.loader.load(args, **kws)
        self.set_contents(contents)
    
    #---------------------------------------------------------------------------
    def cmd_break(self, args, kws):
        self.do_break = True
    
    #---------------------------------------------------------------------------
    def cmd_echo(self, args, kws):
        verbose('>>> {}', args)
    
    #---------------------------------------------------------------------------
    @content_command
    def cmd_dumps(self, content, args, kws):
        print unicode(content)
        print
        return content
    
    #---------------------------------------------------------------------------
    @content_command
    def cmd_text(self, content, args, kws):
        if not isinstance(content, snarf.Text):
            content = snarf.Text(unicode(content))
        return content
    
    #---------------------------------------------------------------------------
    @content_command
    def cmd_html(self, content, args, kws):
        return snarf.HTML(unicode(content))
    
    #---------------------------------------------------------------------------
    @content_command
    def cmd_lines(self, content, args, kws):
        return snarf.Lines(unicode(content))

    #---------------------------------------------------------------------------
    @content_command
    def cmd_write(self, content, args, kws):
        data = '\n'.join([unicode(c) for c in self.contents])
        utils.write_file(args[0], data)

    #---------------------------------------------------------------------------
    # Lines methods
    #---------------------------------------------------------------------------

    #---------------------------------------------------------------------------
    @content_command
    def cmd_skip_to(self, lines, args, kws):
        return lines.skip_to(*args, **kws)
    
    #---------------------------------------------------------------------------
    @content_command
    def cmd_read_until(self, lines, args, kws):
        return lines.read_until(*args, **kws)

    #---------------------------------------------------------------------------
    @content_command
    def cmd_strip(self, lines, args, kws):
        return lines.strip()
    
    #---------------------------------------------------------------------------
    @content_command
    def cmd_end(self, lines, args, kws):
        return lines.end()
    
    #---------------------------------------------------------------------------
    @content_command
    def cmd_matches(self, lines, args, kws):
        return lines.matches(args[0], **kws)
    
    #---------------------------------------------------------------------------
    @content_command
    def cmd_compress(self, lines, args, kws):
        return lines.compress()
    
    #---------------------------------------------------------------------------
    # Text methods
    #---------------------------------------------------------------------------

    #---------------------------------------------------------------------------
    @content_command
    def cmd_normalize(self, text, args, kws):
        return text.normalize()
    
    #---------------------------------------------------------------------------
    @content_command
    def cmd_remove_attrs(self, text, args, kws):
        return text.remove_attrs(args[0] if args else None, **kws)
    
    #---------------------------------------------------------------------------
    @content_command
    def cmd_remove(self, text, args, kws):
        return text.remove_all(args, **kws)
    
    #---------------------------------------------------------------------------
    @content_command
    def cmd_replace(self, text, args, kws):
        args = args[:]
        replacement = args.pop()
        args = [(a, replacement) for a in args]
        return text.replace_all(args, **kws)
    
    #---------------------------------------------------------------------------
    @content_command
    def cmd_unwrap(self, text, args, kws):
        for tag in args:
            text = text.unwrap(tag, **kws)
        
        return text

    #---------------------------------------------------------------------------
    @content_command
    def cmd_extract(self, text, args, kws):
        for tag in args:
            text = text.extract(tag, **kws)
        
        return text
    
    #---------------------------------------------------------------------------
    @content_command
    def cmd_select(self, text, args, kws):
        for arg in args:
            text = text.select(arg)
        
        return text

#-------------------------------------------------------------------------------
def execute_script(filename, contents):
    code = utils.read_file(filename)
    scr = Script(code, contents)
    return scr.execute()
