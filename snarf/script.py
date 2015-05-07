import json
from . import utils
from . import snarf

verbose = utils.verbose

#-------------------------------------------------------------------------------
def scan_script(text):
    instructions = []
    for i, line in enumerate(text.splitlines()):
        line = line.rstrip()
        if not line or line.lstrip().startswith('#'):
            continue
        instructions.append((line, i + 1))
    
    verbose('Scanned {} lines from {} bytes', len(instructions), len(text))
    return instructions


#===============================================================================
class Script(object):
    
    #---------------------------------------------------------------------------
    def __init__(self, obj, is_text=False):
        if not is_text:
            verbose('Reading script file {}', obj)
            obj = utils.read_file(obj)
        
        self.lines = scan_script(obj)
        self.instructions = self.parse(self.lines)
    
    #---------------------------------------------------------------------------
    def parse(self, lines):
        instrs = []
        for line, lineno in lines:
            bits = line.split(' ', 1)
            if len(bits) == 1:
                bits.append('')
            
            instrs.append(('cmd_' + bits[0], bits[1].strip(), lineno))
        return instrs
    
    #---------------------------------------------------------------------------
    def execute(self, content):
        content = self.cmd_text(content)
        for cmd, args, lineno in self.instructions:
            method = getattr(self, cmd, None)
            if method is None:
                raise RuntimeError('Unknown script instruction: ' + cmd)
            
            try:
                content = method(content, args)
            except Exception as exc:
                exc.args += ('Line {}'.format(lineno),)
                raise
            verbose('Executed {}; content: {}({})', cmd, content.__class__.__name__, len(content))

        return content

    #---------------------------------------------------------------------------
    def cmd_break(self, content, args=''):
        utils.pdb.set_trace()
        return content
    
    #---------------------------------------------------------------------------
    def cmd_echo(self, content, args=''):
        verbose('>>> {}', args)
        return content
    
    #---------------------------------------------------------------------------
    def cmd_text(self, content, args=''):
        if not isinstance(content, snarf.Text):
            content = snarf.Text(unicode(content))
        return content
    
    #---------------------------------------------------------------------------
    def cmd_lines(self, content, args=''):
        return snarf.Lines(unicode(content))

    #---------------------------------------------------------------------------
    # Lines methods
    #---------------------------------------------------------------------------

    #---------------------------------------------------------------------------
    def cmd_skip_to(self, lines, args):
        return lines.skip_to(args)
    
    #---------------------------------------------------------------------------
    def cmd_read_until(self, lines, args):
        return lines.read_until(args)

    #---------------------------------------------------------------------------
    def cmd_strip(self, lines, args):
        return lines.strip()
    
    #---------------------------------------------------------------------------
    def cmd_end(self, lines, args):
        return lines.end()
    
    #---------------------------------------------------------------------------
    # Text methods
    #---------------------------------------------------------------------------

    #---------------------------------------------------------------------------
    def cmd_normalize(self, text, args):
        return text.normalize()
    
    #---------------------------------------------------------------------------
    def cmd_remove_attrs(self, text, args):
        if args:
            args = args.split(',')
        return text.remove_attrs(args)
    
    #---------------------------------------------------------------------------
    def cmd_remove(self, text, args):
        return text.remove(args)
    
    #---------------------------------------------------------------------------
    def cmd_replace(self, text, args):
        return text.replace(args)
    
    #---------------------------------------------------------------------------
    def cmd_remove_tags(self, text, args):
        if args:
            args = args.split(',')
        return text.remove_tags(args)
    


#-------------------------------------------------------------------------------
def execute_script(filename, contents):
    script = Script(filename)
    results = []
    if not contents:
        contents = ['']
    for content in contents:
        results.append(script.execute(content))
        
    return results
