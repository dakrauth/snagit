import os
import re
import json
from pprint import pformat
from . import utils
from . import snarf

verbose = utils.verbose
set_trace = utils.pdb.set_trace

#-------------------------------------------------------------------------------
def escaped(txt):
    for cin, cout in (
        ('\\n', '\n'),
        ('\\t', '\t')
    ):
        txt = txt.replace(cin, cout)
    return txt


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
            return re.compile(escaped(s[2:-1]))
        
        return escaped(s[1:-1])

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
    def __init__(self, code=''):
        self.lineno = 1
        self.code = ''
        self.lines = []
        self.instructions = []
        if code:
            self.compile(code)

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


#-------------------------------------------------------------------------------
def register_handler(cls):
    def decorator(method):
        def adapter(self, content, args, kws):
            if cls and not isinstance(content, cls):
                content = cls(unicode(content))
            return method(self, content, args, kws)
        adapter.takes_content = True
        return adapter
    return decorator


html_handler = register_handler(snarf.HTML)
text_handler = register_handler(snarf.Text)
line_handler = register_handler(snarf.Lines)
generic_handler = register_handler(None)


#===============================================================================
class Script(object):
    
    #---------------------------------------------------------------------------
    def __init__(self, code='', contents=None, loader=None, use_cache=False):
        self.loader = loader if loader else utils.Loader(use_cache)
        self.set_contents(contents)
        self.do_break = False
        self.program = Program(code)
        
    #---------------------------------------------------------------------------
    def set_contents(self, contents):
        self.contents = []
        if contents:
            if utils.is_string(contents):
                contents = [contents]
            
            for content in contents:
                if not isinstance(content, snarf.Bits):
                    if utils.is_string(content):
                        c = content.strip()
                        content = (
                            snarf.HTML(content)
                            if c.startswith('<') and c.endswith('>')
                            else snarf.Text(content)
                        )
                    else:
                        content = snarf.Lines(unicode(content))
                        
                self.contents.append(content)
    
    #---------------------------------------------------------------------------
    def get_command(self, cmd):
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
                    if do_break: set_trace()
                    new_content = method(content, instr.args, instr.kws)
                except Exception as exc:
                    exc.args += ('Line {}'.format(instr.lineno),)
                    raise
                else:
                    new_contents.append(new_content)
        
            self.contents = new_contents
        else:
            try:
                if do_break: set_trace()
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
    def cmd_combine(self, args, kws):
        if len(self.contents) > 1:
            self.set_contents(Bits.combine(self.contents))
    
    #---------------------------------------------------------------------------
    def cmd_serialize(self, args, kws):
        self.cmd_combine((), {})
        content = self.contents[0]
        self.set_contents(content.serialize(args, **kws))
    
    #---------------------------------------------------------------------------
    def cmd_cache(self, args, kws):
        self.loader.use_cache()
    
    #---------------------------------------------------------------------------
    def cmd_load(self, args, kws):
        contents = self.loader.load(args, **kws)
        self.set_contents(contents)
    
    #---------------------------------------------------------------------------
    def cmd_load_all(self, args, kws):
        sources = []
        for content in self.contents:
            sources.extend(list(content))
        
        self.cmd_load(sources, **kws)
    
    #---------------------------------------------------------------------------
    def cmd_break(self, args, kws):
        self.do_break = True
    
    #---------------------------------------------------------------------------
    def cmd_echo(self, args, kws):
        verbose('>>> {}', args)
    
    #---------------------------------------------------------------------------
    @generic_handler
    def cmd_dumps(self, content, args, kws):
        print unicode(content)
        return content
    
    #---------------------------------------------------------------------------
    @generic_handler
    def cmd_text(self, content, args, kws):
        return content.text
    
    #---------------------------------------------------------------------------
    @generic_handler
    def cmd_html(self, content, args, kws):
        return content.html
    
    #---------------------------------------------------------------------------
    @generic_handler
    def cmd_lines(self, content, args, kws):
        return content.lines

    #---------------------------------------------------------------------------
    @generic_handler
    def cmd_write(self, content, args, kws):
        data = '\n'.join([unicode(c) for c in self.contents])
        utils.write_file(args[0], data)

    #---------------------------------------------------------------------------
    # Lines methods
    #---------------------------------------------------------------------------

    #---------------------------------------------------------------------------
    @line_handler
    def cmd_skip_to(self, lines, args, kws):
        return lines.skip_to(*args, **kws)
    
    #---------------------------------------------------------------------------
    @line_handler
    def cmd_read_until(self, lines, args, kws):
        return lines.read_until(*args, **kws)

    #---------------------------------------------------------------------------
    @line_handler
    def cmd_strip(self, lines, args, kws):
        return lines.strip()
    
    #---------------------------------------------------------------------------
    @line_handler
    def cmd_end(self, lines, args, kws):
        return lines.end()
    
    #---------------------------------------------------------------------------
    @line_handler
    def cmd_matches(self, lines, args, kws):
        return lines.matches(args[0], **kws)
    
    #---------------------------------------------------------------------------
    @line_handler
    def cmd_compress(self, lines, args, kws):
        return lines.compress()

    #---------------------------------------------------------------------------
    @line_handler
    def cmd_format(self, lines, args, kws):
        return lines.format(args[0])
    
    #---------------------------------------------------------------------------
    # Text methods
    #---------------------------------------------------------------------------

    #---------------------------------------------------------------------------
    @text_handler
    def cmd_remove(self, text, args, kws):
        return text.remove_all(args, **kws)
    
    #---------------------------------------------------------------------------
    @text_handler
    def cmd_replace(self, text, args, kws):
        args = args[:]
        replacement = args.pop()
        args = [(a, replacement) for a in args]
        return text.replace_all(args, **kws)
    
    #---------------------------------------------------------------------------
    # HTML methods
    #---------------------------------------------------------------------------

    #---------------------------------------------------------------------------
    @html_handler
    def cmd_remove_attrs(self, text, args, kws):
        return text.remove_attrs(args[0] if args else None, **kws)
    
    #---------------------------------------------------------------------------
    @html_handler
    def cmd_unwrap(self, text, args, kws):
        for tag in args:
            text = text.unwrap(tag, **kws)
        
        return text

    #---------------------------------------------------------------------------
    @html_handler
    def cmd_extract(self, text, args, kws):
        for tag in args:
            text = text.extract(tag, **kws)
        
        return text
    
    #---------------------------------------------------------------------------
    @html_handler
    def cmd_select(self, text, args, kws):
        return text.select(args[0])

    #---------------------------------------------------------------------------
    @html_handler
    def cmd_select_attr(self, text, args, kws):
        results = text.select_attr(args[0], args[1])
        return snarf.Lines(results)
        
    #---------------------------------------------------------------------------
    @html_handler
    def cmd_replace_tag(self, text, args, kws):
        return text.replace_with(args[0], args[1])
    
    #---------------------------------------------------------------------------
    @html_handler
    def cmd_collapse(self, text, args, kws):
        for arg in args:
            text = text.collapse(arg, **kws)
        return text
    
    
#-------------------------------------------------------------------------------
def execute_script(filename, contents):
    code = utils.read_file(filename)
    scr = Script(code, contents)
    return scr.execute()
