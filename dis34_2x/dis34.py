"""Disassembler of Python byte code into mnemonics."""

import sys
import types
import collections

from opcode import *
from opcode import __all__ as _opcodes_all
from itertools import izip
from io import open

__all__ = ["code_info", "dis", "disassemble", "distb", "disco",
           "findlinestarts", "findlabels", "show_code",
           "get_instructions", "Instruction"] + _opcodes_all
del _opcodes_all

_have_code = (types.MethodType, types.FunctionType, types.CodeType, type)

def _try_compile(source, name):
    """Attempts to compile the given source, first as an expression and
       then as a statement if the first approach fails.

       Utility function to accept strings in functions that otherwise
       expect code objects
    """
    try:
        c = compile(source, name, 'eval')
    except SyntaxError:
        c = compile(source, name, 'exec')
    return c

def dis(x=None, **_3to2kwargs):
    """Disassemble classes, methods, functions, or code.

    With no argument, disassemble the last traceback.

    """
    if 'file' in _3to2kwargs: file = _3to2kwargs['file']; del _3to2kwargs['file']
    else: file = sys.stdout
    if x is None:
        distb()
        return
    if isinstance(x, types.InstanceType):
        x = x.__class__    
    if hasattr(x, 'im_func'):  # Method
        x = x.im_func
    if hasattr(x, 'func_code'):  # Function
        x = x.func_code
    if hasattr(x, '__dict__'):  # Class or module
        items = sorted(x.__dict__.items())
        for name, x1 in items:
            if isinstance(x1, _have_code):
                print >>file, "Disassembly of %s:" % name
                try:
                    dis(x1)
                except TypeError, msg:
                    print >>file, "Sorry:", msg
                print >>file
    elif hasattr(x, 'co_code'): # Code object
        disassemble(x, file=file)
    elif isinstance(x, bytearray): # Raw bytecode
        _disassemble_bytes(x, file=file)
    elif isinstance(x, (str, unicode)):    # Source code
        _disassemble_str(x, file=file)
    else:
        raise TypeError("don't know how to disassemble %s objects" %
                        type(x).__name__)

def distb(tb=None, **_3to2kwargs):
    """Disassemble a traceback (default: last traceback)."""
    if 'file' in _3to2kwargs: file = _3to2kwargs['file']; del _3to2kwargs['file']
    else: file = sys.stdout
    if tb is None:
        try:
            tb = sys.last_traceback
        except AttributeError:
            raise RuntimeError("no last traceback to disassemble")
        while tb.tb_next: tb = tb.tb_next
    disassemble(tb.tb_frame.f_code, tb.tb_lasti, file=file)

# The inspect module interrogates this dictionary to build its
# list of CO_* constants. It is also used by pretty_flags to
# turn the co_flags field into a human readable list.
COMPILER_FLAG_NAMES = {
     1: "OPTIMIZED",
     2: "NEWLOCALS",
     4: "VARARGS",
     8: "VARKEYWORDS",
    16: "NESTED",
    32: "GENERATOR",
    64: "NOFREE",
}

def pretty_flags(flags):
    """Return pretty representation of code flags."""
    names = []
    for i in xrange(32):
        flag = 1<<i
        if flags & flag:
            names.append(COMPILER_FLAG_NAMES.get(flag, hex(flag)))
            flags ^= flag
            if not flags:
                break
    else:
        names.append(hex(flags))
    return ", ".join(names)

def _get_code_object(x):
    """Helper to handle methods, functions, strings and raw code objects"""
    if hasattr(x, 'im.func'): # Method
        x = x.im_func
    if hasattr(x, 'func_code'): # Function
        x = x.func_code
    if isinstance(x, (str, unicode)):     # Source code
        x = _try_compile(x, "<disassembly>")
    if hasattr(x, 'co_code'):  # Code object
        return x
    raise TypeError("don't know how to disassemble %s objects" %
                    type(x).__name__)
    
def code_info(x):
    """Formatted details of methods, functions, or code."""
    return _format_code_info(_get_code_object(x))

def _format_code_info(co):
    lines = []
    lines.append("Name:              %s" % co.co_name)
    lines.append("Filename:          %s" % co.co_filename)
    lines.append("Argument count:    %s" % co.co_argcount)
    lines.append("Kw-only arguments: %s" % co.co_kwonlyargcount)
    lines.append("Number of locals:  %s" % co.co_nlocals)
    lines.append("Stack size:        %s" % co.co_stacksize)
    lines.append("Flags:             %s" % pretty_flags(co.co_flags))
    if co.co_consts:
        lines.append("Constants:")
        for i_c in enumerate(co.co_consts):
            lines.append("%4d: %r" % i_c)
    if co.co_names:
        lines.append("Names:")
        for i_n in enumerate(co.co_names):
            lines.append("%4d: %s" % i_n)
    if co.co_varnames:
        lines.append("Variable names:")
        for i_n in enumerate(co.co_varnames):
            lines.append("%4d: %s" % i_n)
    if co.co_freevars:
        lines.append("Free variables:")
        for i_n in enumerate(co.co_freevars):
            lines.append("%4d: %s" % i_n)
    if co.co_cellvars:
        lines.append("Cell variables:")
        for i_n in enumerate(co.co_cellvars):
            lines.append("%4d: %s" % i_n)
    return "\n".join(lines)

def show_code(co, **_3to2kwargs):
    """Print details of methods, functions, or code to stdout."""
    if 'file' in _3to2kwargs: file = _3to2kwargs['file']; del _3to2kwargs['file']
    else: file = sys.stdout
    print >>file, code_info(co)

_Instruction = collections.namedtuple("_Instruction",
     "opname opcode arg argval argrepr offset starts_line is_jump_target") 

class Instruction(_Instruction):
    """Details for a bytecode operation
    
       Defined fields:
         opname - human readable name for operation
         opcode - numeric code for operation
         arg - numeric argument to operation (if any), otherwise None
         argval - resolved arg value (if known), otherwise same as arg
         argrepr - human readable description of operation argument
         offset - start index of operation within bytecode sequence
         starts_line - line started by this opcode (if any), otherwise None
         is_jump_target - True if other code jumps to here, otherwise False
    """

    def _disassemble(self, lineno_width=3, mark_as_current=False):
        """Format instruction details for inclusion in disassembly output
        
        *lineno_width* sets the width of the line number field (0 omits it)
        *mark_as_current* inserts a '-->' marker arrow as part of the line
        """
        fields = []
        # Column: Source code line number
        if lineno_width:
            if self.starts_line is not None:
                lineno_fmt = "%%%dd" % lineno_width
                fields.append(lineno_fmt % self.starts_line)
            else:
                fields.append(' ' * lineno_width)
        # Column: Current instruction indicator
        if mark_as_current:
            fields.append('-->')
        else:
            fields.append('   ')
        # Column: Jump target marker
        if self.is_jump_target:
            fields.append('>>')
        else:
            fields.append('  ')
        # Column: Instruction offset from start of code sequence
        fields.append(repr(self.offset).rjust(4))
        # Column: Opcode name
        fields.append(self.opname.ljust(20))
        # Column: Opcode argument
        if self.arg is not None:
            fields.append(repr(self.arg).rjust(5))
            # Column: Opcode argument details
            if self.argrepr:
                fields.append('(' + self.argrepr + ')')
        return ' '.join(fields)


def get_instructions(x, **_3to2kwargs):
    """Iterator for the opcodes in methods, functions or code

    Generates a series of Instruction named tuples giving the details of
    each operations in the supplied code.
    
    The given line offset is added to the 'starts_line' attribute of any
    instructions that start a new line.
    """
    if 'line_offset' in _3to2kwargs: line_offset = _3to2kwargs['line_offset']; del _3to2kwargs['line_offset']
    else: line_offset = 0
    co = _get_code_object(x)
    cell_names = co.co_cellvars + co.co_freevars
    linestarts = dict(findlinestarts(co))
    return _get_instructions_bytes(co.co_code, co.co_varnames, co.co_names,
                                   co.co_consts, cell_names, linestarts,
                                   line_offset)

def _get_arg_info(arg, info_source):
    """Helper to get optional details about the operation argument
    
       Returns the dereferenced argval and its repr() if the info
       source is defined.
       Otherwise return the arg and its repr().
    """
    argval = arg
    if info_source is not None:
        argval = info_source[arg]
    if isinstance(argval, str):
        details = argval
    else:
        details = repr(argval)
    return argval, details


def _get_instructions_bytes(code, varnames=None, names=None, constants=None,
                      cells=None, linestarts=None, line_offset=0):
    """Iterate over the instructions in a bytecode string.

    Generates a sequence of Instruction namedtuples giving the details of each
    opcode.  Additional information about the code's runtime environment
    (e.g. variable names, constants) can be specified using optional
    arguments.

    """
    labels = findlabels(code)
    extended_arg = 0
    starts_line = None
    free = None
    # enumerate() is not an option, since we sometimes process
    # multiple elements on a single pass through the loop
    n = len(code)
    i = 0
    while i < n:
        op = ord(code[i])
        offset = i
        if linestarts is not None:
            starts_line = linestarts.get(i, None)
            if starts_line is not None:
                starts_line += line_offset
        is_jump_target = i in labels
        i = i+1
        arg = None
        argval = None
        argrepr = ''
        if op >= HAVE_ARGUMENT:
            arg = ord(code[i]) + ord(code[i+1])*256 + extended_arg
            extended_arg = 0
            i = i+2
            if op == EXTENDED_ARG:
                extended_arg = arg*65536
            #  Set argval to the dereferenced value of the argument when
            #  availabe, and argrepr to the string representation of argval.
            #    _disassemble_bytes needs the string repr of the
            #    raw name index for LOAD_GLOBAL, LOAD_CONST, etc.
            argval = arg
            if op in hasconst:
                argval, argrepr = _get_arg_info(arg, constants)
            elif op in hasname:
                argval, argrepr = _get_arg_info(arg, names)
            elif op in hasjrel:
                argval = i + arg
                argrepr = "to " + repr(argval)
            elif op in haslocal:
                argval, argrepr = _get_arg_info(arg, varnames)
            elif op in hascompare:
                argval = cmp_op[arg]
                argrepr = argval
            elif op in hasfree:
                argval, argrepr = _get_arg_info(arg, cells)
        yield Instruction(opname[op], op,
                          arg, argval, argrepr,
                          offset, starts_line, is_jump_target)

def disassemble(co, lasti=-1, **_3to2kwargs):
    """Disassemble a code object."""
    if 'file' in _3to2kwargs: file = _3to2kwargs['file']; del _3to2kwargs['file']
    else: file = sys.stdout
    cell_names = co.co_cellvars + co.co_freevars
    linestarts = dict(findlinestarts(co))
    _disassemble_bytes(co.co_code, lasti, co.co_varnames, co.co_names,
                       co.co_consts, cell_names, linestarts, file=file)

def _disassemble_bytes(code, lasti=-1, varnames=None, names=None,
                       constants=None, cells=None, linestarts=None, 
                       **_3to2kwargs):
    if 'file' in _3to2kwargs: file = _3to2kwargs['file']; del _3to2kwargs['file']
    else: file = sys.stdout
    # Omit the line number column entirely if we have no line number info
    show_lineno = linestarts is not None
    # TODO?: Adjust width upwards if max(linestarts.values()) >= 1000?
    lineno_width = 3 if show_lineno else 0
    for instr in _get_instructions_bytes(code, varnames, names,
                                         constants, cells, linestarts):
        new_source_line = (show_lineno and
                           instr.starts_line is not None and
                           instr.offset > 0)
        if new_source_line:
            print >>file
        is_current_instr = instr.offset == lasti
        print >>file, instr._disassemble(lineno_width, is_current_instr)
 
def _disassemble_str(source, **_3to2kwargs):
    """Compile the source string, then disassemble the code object."""
    if 'file' in _3to2kwargs: file = _3to2kwargs['file']; del _3to2kwargs['file']
    else: file = sys.stdout
    disassemble(_try_compile(source, '<dis>'), file=file)

disco = disassemble                     # XXX For backwards compatibility

def findlabels(code):
    """Detect all offsets in a byte code which are jump targets.

    Return the list of offsets.

    """
    labels = []
    # enumerate() is not an option, since we sometimes process
    # multiple elements on a single pass through the loop
    n = len(code)
    i = 0
    while i < n:
        op = ord(code[i])
        i = i+1
        if op >= HAVE_ARGUMENT:
            arg = ord(code[i]) + ord(code[i+1])*256
            i = i+2
            label = -1
            if op in hasjrel:
                label = i+arg
            elif op in hasjabs:
                label = arg
            if label >= 0:
                if label not in labels:
                    labels.append(label)
    return labels

def findlinestarts(code):
    """Find the offsets in a byte code which are start of lines in the source.

    Generate pairs (offset, lineno) as described in Python/compile.c.

    """
    byte_increments = [ord(c) for c in code.co_lnotab[0::2]]
    line_increments = [ord(c) for c in code.co_lnotab[1::2]]

    lastlineno = None
    lineno = code.co_firstlineno
    addr = 0
    for byte_incr, line_incr in izip(byte_increments, line_increments):
        if byte_incr:
            if lineno != lastlineno:
                yield (addr, lineno)
                lastlineno = lineno
            addr += byte_incr
        lineno += line_incr
    if lineno != lastlineno:
        yield (addr, lineno)

class Bytecode(object):
    """The bytecode operations of a piece of code
    
    Instantiate this with a function, method, string of code, or a code object
    (as returned by compile()).
    
    Iterating over this yields the bytecode operations as Instruction instances.
    """
    def __init__(self, x):
        self.codeobj = _get_code_object(x)
        self.cell_names = self.codeobj.co_cellvars + self.codeobj.co_freevars
        self.linestarts = dict(findlinestarts(self.codeobj))
        self.line_offset = 0
        self.original_object = x
    
    def __iter__(self):
        co = self.codeobj
        return _get_instructions_bytes(co.co_code, co.co_varnames, co.co_names,
                                   co.co_consts, self.cell_names,
                                   self.linestarts, self.line_offset)
    
    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, self.original_object)
    
    def info(self):
        """Return formatted information about the code object."""
        return _format_code_info(self.codeobj)
    
    def show_info(self, **_3to2kwargs):
        """Print the information about the code object as returned by info()."""
        if 'file' in _3to2kwargs: file = _3to2kwargs['file']; del _3to2kwargs['file']
        else: file = sys.stdout
        print >>file, self.info()
    
    def display_code(self, **_3to2kwargs):
        """Print a formatted view of the bytecode operations.
        """
        if 'file' in _3to2kwargs: file = _3to2kwargs['file']; del _3to2kwargs['file']
        else: file = sys.stdout
        co = self.codeobj
        return _disassemble_bytes(co.co_code, varnames=co.co_varnames,
                                  names=co.co_names, constants=co.co_consts,
                                  cells=self.cell_names,
                                  linestarts=self.linestarts,
                                  file=file
                                 )
        

def _test():
    """Simple test program to disassemble a file."""
    if sys.argv[1:]:
        if sys.argv[2:]:
            sys.stderr.write("usage: python dis.py [-|file]\n")
            sys.exit(2)
        fn = sys.argv[1]
        if not fn or fn == "-":
            fn = None
    else:
        fn = None
    if fn is None:
        f = sys.stdin
    else:
        f = open(fn)
    source = f.read()
    if fn is not None:
        f.close()
    else:
        fn = "<stdin>"
    code = compile(source, fn, "exec")
    dis(code)

if __name__ == "__main__":
    _test()
