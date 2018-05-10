""" 
    splain.py -- explain exceptions and offer debugging advice 
                 NOTE that this program buffers STDERR until
                 program termination

    Author:      David Blaikie (david@davidbpython.com)

    Version:     0.1.1

    Last revised:  2017-05-10


    To use, simply place splain.py in your Python search path;
    in your script, import splain

"""
import __main__ as main
if not hasattr(main, '__file__'):
    raise ImportError('splain cannot be imported from the interactive Python interpreter')


import sys
import atexit
import io
import os
import re
import textwrap

STRING_INDENT = 5
WRAP_WIDTH = 75
EXCEP_BAR_WIDTH = 40
TRACEBACK_STRING = 'Traceback (most recent call last):'
PYTHON_MAJOR_VERSION = sys.version_info[0]



if PYTHON_MAJOR_VERSION != 3:
    raise ValueError('splain.py is usable only with Python 3')

import urllib
from urllib import request
from urllib.parse import urlencode, quote_plus

class ExceptionNotImplementedError(Exception):
    pass


class Splain:

    """
        .type
        .headline
        .desc
        .blocks    # 'debug', 'error_message' (for now)
    """
    def __init__(self, xcep):
        self.__dict__ = Splain.parse_splaintext(xcep.type)
        for key in self.__dict__:
            for xc_key in xcep.__dict__:
                try:
                    self.__dict__[key] = self.__dict__[key].format(**{xc_key: xcep.__dict__[xc_key]})
                except KeyError:
                    pass
        self.type = xcep.type
        self.exception = xcep


    @staticmethod
    def wrap_paragraphs(text, indent=STRING_INDENT, 
                              subsequent_indent=STRING_INDENT):

        indent = ' ' * indent
        subsequent_indent = ' ' * subsequent_indent

        TEXTWRAP_ARGS = { 'width': WRAP_WIDTH,
                          'replace_whitespace': False, 
                          'initial_indent': indent,
                          'subsequent_indent': subsequent_indent }
        paragraphs = text.split('\n\n')

        wrapped_paragraphs = []
        for par in paragraphs:
            wpar = '\n'.join(textwrap.wrap(par, **TEXTWRAP_ARGS))
            wrapped_paragraphs.append(wpar)
        return '\n\n'.join(wrapped_paragraphs)


    def explain(self):
        type_headline_sep = ':  '

        desc = Splain.wrap_paragraphs(self.desc)
        debug = Splain.wrap_paragraphs(self.debug)
        debug_strategy = Splain.wrap_paragraphs(self.debug_strategy)

        headline = Splain.wrap_paragraphs(self.type + type_headline_sep + self.headline, indent=0, subsequent_indent=len(self.type) + 3)

        type_headline_bar = WRAP_WIDTH * '='
        excep_headline_bar = WRAP_WIDTH * '='

        excep_out = """{excep_headline_bar}
{excep_text}
{excep_headline_bar}
""".format(excep_headline_bar=excep_headline_bar,
           excep_text=self.exception.text.strip())

#{s.type}{type_headline_sep}{s.headline}
        short_out = """{type_headline_bar}
{headline}
{type_headline_bar}

ERROR MESSAGE
    {e.msg}


ERROR LINE
{e.line_no}    {e.code_line}


DEBUG STRATEGY
{debug_strategy}
""".format(type_headline_bar=type_headline_bar,
           type_headline_sep=type_headline_sep,
           s=self,
           e=self.exception,
           debug_strategy=debug_strategy,
           headline=headline)

        long_out = """
EXPLANATION
{desc}


DEBUGGING
{debug}
""".format(desc=desc,
           debug=debug)

        if self.exception.prev_stderr_text:
                print(self.exception.prev_stderr_text)
        print(excep_out)
        print()
        print(short_out)
        ui = input("Press 'c' for more splain, [Enter] to quit:  ")
        if ui == 'c':
            print()
            print(long_out)


    @staticmethod
    def parse_splaintext(selected_type):

        text = EXCEP_CONTENT.strip()
        
        splain_dict = {}
        excep_blocks = re.split(r'\n=====\n', text)
        for excep_block in excep_blocks:
        
            desc_blocks = re.split(r'\n===\n', excep_block)
        
            head_block = desc_blocks[0]
            desc_blocks = desc_blocks[1:]
        
            # head block:  excep_type, excep_headline, excep_desc
            head_lines = head_block.splitlines()
            excep_type = head_lines[0].strip()
            excep_headline = head_lines[1].strip()

            if not len(head_lines) > 2:
                excep_desc = ''
        
            elif len(head_lines) == 3 and re.search(r'^\s*$', head_lines[2]):
                excep_desc = ''
        
            elif not re.search(r'^\s*$', head_lines[2]):
                raise ValueError('head block for {} not followed by '
                                 'blank line'.format(excep_type))
        
            elif not len(head_lines) > 3:
                excep_desc = ''
        
            else:
                excep_desc = '\n'.join(head_lines[3:])
        
            splain_dict[excep_type] = { 'headline': excep_headline,
                                        'desc': excep_desc           }
        
            for block in desc_blocks:
                block_lines = block.splitlines()
                block_type = block_lines[0].strip()
                block_text = '\n'.join(block_lines[1:])
                splain_dict[excep_type][block_type.lower()] = block_text

        if selected_type not in splain_dict:
            if PYTHON_MAJOR_VERSION == 3:
                try:
                    send_log(selected_type, 'NOT_IMPLEMENTED', '', '', '')
                except urllib.error.URLError:
                    pass
            raise ExceptionNotImplementedError

        return splain_dict[selected_type]


class Excep:

    def __init__(self, text):

        self.text = text

        lines = text.splitlines()
        announce_line, file_line = lines[0:2]
        code_line, error_line = lines[-2:]

        self.announce = announce_line
        self.filepath = re.search(r'File "(.+?)"', file_line).group(1)
        self.filename = os.path.basename(self.filepath)
        self.line_no = re.search(r'line (\d+),', file_line).group(1)
        self.code_line = code_line
        self.error_line = error_line 
        self.type = re.search(r'([^:]+)', error_line).group(1)

        try:
            self.msg = re.search(self.type + r': (.+)', error_line).group(1)
        except AttributeError:
            self.msg = ''

        # ,splain:  a Splain object (.type, .headline, .desc, .blocks)
        self.splain = Splain(self)




def read_stderr():
    """ at exit of program, read string holding STDERR output.
        if it looks like an exception, start explaining.
        if not, write it to the real sys.stderr """

    sys.stderr.seek(0)
    text = sys.stderr.read()
    sys.stderr = sys.__stderr__

    if TRACEBACK_STRING in text:
        if not text.startswith(TRACEBACK_STRING):
            prev_stderr_text = text[0:text.index(TRACEBACK_STRING)]
            text = text[text.index(TRACEBACK_STRING):]
        else:
            prev_stderr_text = ''

        try:
            explain(text, prev_stderr_text)
        except ExceptionNotImplementedError:
            sys.stderr.write(prev_stderr_text + text)

    else:
        sys.stderr.write(text)


def explain(exception_text, prev_stderr_text):

    # Excep object describes the exception error string
    xc = Excep(exception_text)
    xc.prev_stderr_text = prev_stderr_text

    if PYTHON_MAJOR_VERSION == 3:
        try:
            send_log(xc.type, xc.error_line, xc.code_line, xc.line_no, xc.filename)
        except urllib.error.URLError:
            pass

    xc.splain.explain()


def send_log(exc_type, error_line, code_line, line_no, filename):


    url = 'http://lyricalpictures.com/cgi-bin/splain_log.cgi'

    payload = { 'exc_type': exc_type,
                'error_line': error_line,
                'code_line': code_line,
                'line_no': line_no, 
                'filename': filename }

    query_string = urlencode(payload, quote_via=quote_plus)

    request.urlopen(url + '?' + query_string)
   











EXCEP_CONTENT = """
AttributeError
The code attempted to access an attribute (i.e., "object.attribute") that doesn't exist for that object.

An "attribute" is the name after a object and a period, i.e. "object.attribute' -- for example 'sys.argv', 'os.listdir' or 'mystring.rstrip'.  Anytime you see this "dot syntax", the name before the period is the object and the name after the period is the attribute.  

A method is a type of attribute, and follows the same syntax -- for ezxample 'mylist.append()', 'mystring.strip()', etc.  An AttributeError exception often refers to a method; the code is usually rejecting a method call that is not available on the object.  For example, the 'str' object has an rstrip() method/attribute, but this attribute is not supported by a list.  So if you tried to call mylist.rstrip(), Python raises AttributeError.  To determine the proper object or attribute, you can review the most common methods for each of the core Python object types in the Executive Summary.  
===
ERROR_MESSAGE
The message most often names the type of the object and the name of the attribute, as in ("dict" object has not attribue "append").  
===
DEBUG_STRATEGY
In the error line, identify the object and the attribute; correct object type or attribute.
===
DEBUG
Read the error message and then identify the object and attribute in the error line -- this should be straightforward, since the error line should display the object followed by a dot followed by the attribute name ("object.attribute").  The error line explicitly names the object type and the attribute that is not supported by that type.  Use the Executive Summary to review the most common methods for the object type, and consider whether you are using the right object type, or the right method, to achieve your purpose here.  

If you weren't expecting the variable to be of that type, you may want to trace the variable's origin by searching back in the code execution from that line, and seek to find out where that variable was last modified, and/or where and how it was initialized (where it began its existence with "var = something"). 
=====
FileNotFoundError
The code attempted to access a file or directory that does not exist here.

FileNotFoundError is raised when Python asks the OS to perform a filesystem-related task (opening a file, reading a directory, reading a file's size, etc.) but the file or directory doesn't exist on the filesystem.  If the file or directory is a "relative path" (i.e., is just the filename, or a path that doesn't begin with a forward slash (Unix/Mac) or a drive letter (Windows)), then its location is dependent on the "current working directory".
===
DEBUG_STRATEGY
Determine where Python is looking for the file or directory, correct file or filepath.
===
DEBUG
The error message contains the file or filepath in quotes.  The error line (line {line_no}) should contain the string variable or string literal specifying this file/path.

If the file/path is "absolute" (i.e., it begins with a forward slash (Unix/Mac) or drive letter (Windows)), look for this file/path on your system and verify its existence and its correct spelling.

If the file/path is "relative" (i.e., it does not begin with a forward slash (Unix/Mac) or drive letter (Windows), you must first confirm the "current working directory".  Just before the error line ({line_no}), place this statement:

import os; print(os.getcwd())

When you run the program again, you should see this "current working directory" path printed on the line above the exception output.  If the file/path in the error line is relative, Python is looking for the file/path starting from the current working directory (printed by your debug statement).
=====
IndentationError
When reading the script line-by-line, Python found an indent where it wasn't expected, or didn't find an indent where it was expected.

An "indent" refers to code that starts further to the right than the previous code line (blank lines are ignored).  The usual indent size is 4 spaces -- that is, an indented line starts 4 spaces further to the right than the previous line.

Indents MUST occur after the first statement in a compound statement (for example 'if', 'elif', 'else', 'while', 'def', 'class').  Each of these statements ends with a colon, and the line after it is expected to be indented.

Indents CAN occur in one of these other places:
  - inside a triple-quoted string (the indent is part of the string, not evaluated as Python syntax)
  - after an open brace, bracket or parenthesis (Python does not check for indents until it reaches the ending brace, bracket or parenthesis)

Indents CANNOT appear anywhere except as specified above.
===
DEBUG_STRATEGY
Review indenting rules and make sure line in question follows them.  
===
DEBUG
Look closely at the line in question ({line_no}):
  - If it comes after a line ending in a colon (if, elif, etc.), is it indented?
  - If it does not come after a line ending in a colon, does it start at the same horizontal position as the previous code line?
  - Does the indent contain any tabs (while the rest of the program is indented with spaces)?  Tabs and spaces must never be mixed in a program.  You can usually check for tabs by moving your cursor over the indented portion character-by-character and seeing if it jumps more than one space for each tap of the arrow key.
=====
IndexError
The code is attempting to access a sequence item (using an index integer) that doesn't exist in the sequence.

The sequence is often a list, but the tuple object (or any other object that has an index (i.e., whose items can be accessed by index integer) may raise an IndexError if the requested index does not exist.
===
DEBUG_STRATEGY
Print the list or sequence object and index integer just before error line to see why item index doesn't exist in list/sequence.
===
DEBUG
The line in question ({line_no}) should contain a variable followed by a subscript (square brackets) with a variable or an integer literal value inside -- for example, 'mylist[i]', where 'mylist' is the list or sequence object, and 'i' is the integer object.  There are two questions to ask:  how many items are in the list/sequence, and what integer value is in the square brackets?

Just before line {line_no}, add two print statements:  one that prints the len() of the sequence variable (the variable followed by the square brackets), and one that prints the index (the variable in the square brackets).  You should find that the index value is at least two greater than the len() of the sequence (for example if the len() of the sequence is 5, the index value will be 7 or greater).  

You may also want to print the entire list/sequence directly (instead of just its len) if it is small enough to provide clear output (some lists are too big for this).  

Or in rare cases the index will be a negative number -- since negative indices count from the end, you will find that the index is at least one less than the len() of the sequence.
=====
KeyError
The code attempted to access a key that doesn't exist in a dictionary.  

Dictionary subscripts look like list subscripts, e.g. 'mydict[thiskey]' -- where 'mydict' is the dictionary and 'thiskey' is a variable holding a key currently in the dictionary.  If the 'thiskey' variable isn't a key currently in the dictionary, then attempting to access it raises a KeyError.  
===
DEBUG_STRATEGY
Print dictionary (or just dictionary keys) and subscript value to see why the key doesn't appear in the dict.  
===
DEBUG
The line in question ({line_no}) should contain a variable followed by a subscript (square brackets) with a variable or literal value (string or number), inside.  The error line indicates the key that was attempted to be accessed (at the end of the error line, in single quotes).  

If the key that was attempted to be accessed makes sense to you (i.e., you think it should be in the dictionary), the next question to ask is what keys does the dictionary contain?  Just before the error line ({line_no}), add a print statement that prints the keys of the dictionary (this example uses the variable name 'mydict', but you should use the variable name of your dictionary):

print(list(mydict.keys()))

You will of course see that the key that was attempted to be accessed is not in the printed list of keys, but you may also find that the keys that are in the dict are unexpected, or possibly that there are no keys in the dict.

You'll then want to look back to the lines of code that initialize and add to the dict, possibly print the value of the variables that are being added as keys to the dict, and track down the mismatch that led to this exception.

If the key is sometimes in the dict and sometimes not, you'll want to use a conditional (i.e., 'if') to check to see if the key is in the dict before trying to access it, and if not, take other action -- perhaps adding the key to the dictionary.  
=====
ModuleNotFoundError
The code attempted to import a module that isn't built into Python and hasn't been installed.

This error can be caused by these issues:  

- the module name is misspelled

- the module is built into another version of Python, but not the one being used here

- the module has been copied as a .py file to a directory on your system, but Python doesn't know where to find it.  Python consults the "current working directory" as well as the PYTHONPATH environment variable and the sys.path list variable, which contain directories where modules are expected to be found.
===
DEBUG_STRATEGY
Check the spelling of the module name; the module search path (sys.path) and verify location of module to be imported; check what version of Python you are running and whether the module is installed into that version.  
===
DEBUG
- check the spelling of the module name

- check the running version of python -- you can add this code right in the script to show the version running:   

import sys; print(sys.version)

- check the module search paths -- you can add this code right in the script to print this list of paths:  

import sys; print(sys.path)
=====
NameError
The code is referring to a name (of a variable, built-in function, module, exception, etc.) that has not been defined.

Python recognizes some names by default (for example "len" (the function) or "IndexError" (the exception type)).  (Statement terms like "if" and "del" are evaluated as syntax, not as names.)  All other names will be recognized if they have been declared in the code before they are used (for example any variable names used in an assignment statement ("x = 5", "def myfunc:") or "for" looping statement ("for x in y").

Since Python reads a script from top to bottom, the declaration must appear before use.  This applies to all function and class statements as well.

Also names in modules will not be accessible except as attributes of the module name or "import as" name, unless they are imported explicitly into this program.
===
DEBUG_STRATEGY
Check spelling of name; look for variable initialized earlier in code to verify same spelling.  Check scope of variable (local or global?)
===
DEBUG
The name Python couldn't find is in quotes in the error message.  Reflect on this name and search for it within the code to see if or at what point it was defined.

- If you can't find the name anywhere else in the code, it may be misspelled, or you may have forgotten to define it.

- If the name is declared inside a function, then it can be used only inside the function.  If it is needed outside the function, then it must be declared outside the function, or it can be declared inside the function in which it is used.

- If the name is declared inside a conditional block ('if', 'elif', 'else' or 'while') or loop block ('for'), which indicates that the code execution may never have entered the block (to reach the declaration statement).  To see if the block is being entered, place a print statement as the first statement inside the block, indicating that the block has been entered -- if you don't see the statement printed, then the block was never entered:  

  - If the name is declared inside an "if", "elif" or "else" block, consider the conditions that determine whether the block is entered.

  - If the name is declared inside a "while" block, consider the condition specified in the "while" statement (you may want to print this value) -- if it is False, the block is never entered.

  - If the name is declared inside a "for" block, check to see what is inside the iterable (variable or function/method call -- you may want to print this value).  If there is nothing to iterate over, the block will not be entered.
=====
TypeError
The code is using an object in a function call, operation or statement that is not appropriate for that object type.

All object types are defined to "support" a limited set of operations.  For example "-" is supported by numbers and sets, but not strings; "+" is supported by numbers, strings, lists and tuples, but not sets; round() works only with numbers.  One of the operations or function calls on line {line_no} uses an object type in a way that is unsupported by that object.  The error message should indicate the object type in question and the unsupported operation, operator or function.
===
DEBUG_STRATEGY
Print type(s) of object(s) and review docs or examples for proper usage of the attempted function or operation.
===
DEBUG
In the error message, you will usually see the operation that was attempted and the object type(s) involved in the operation, along with an explanation of why these type(s) can't be used (although it may be as simple as "I can't do that").

Looking at the error line ({line_no}), find the operation referenced in the message, then attempt to identify the object(s) involved.  You may want to add print statements just above the error line that print the objects and their types.  Then look for documentation on the operation to see what types are required.  You may need to convert the types of the objects so they can be used here, or you may realize that a different operation or function is needed instead.
=====
UnboundLocalError
The code is attempting to refer to or use a variable inside a function before it was defined.

The most common cause of this exception is when the code attempts to modify a global variable (a variable defined outside a function) by assigning back to it:

x = 0
     def dothis():
        x = x + 1
     dothis()

This code is attempting to increment 'x', but because it is also assigning to 'x' within the function, it thinks that 'x' is a local variable (i.e., local to the function and unavailable outside of it).  Because it thinks that 'x' is a local variable, it can't understand why it is being asked to access the value of 'x' on the right side of that line -- it thinks it is being asked to read the local 'x' before 'x' has even been assigned (since it needs to read 'x' in order to add 1 to 'x').

In a sense, this is a kind of 'NameError' for local variables.  What makes it different is that Python can see that the variable in question is a local variable (because it is being defined inside the function).  But it is also being asked to read from this variable before it is even assigned, so Python generates the error message "local variable referenced before assignment".

If your intention was to increment or modify a global variable, you can use the 'global' statement as the first statement in the function to identify the variable as global.

x = 0
     def kdothis():
         global x
         x = x + 1
     dothis()

However, be advised that modifying a global variable inside a function is not considered to be a good design choice, because it can cause bugs that are difficult to track down.  Instead, you should pass the value to the function as an argument, modify it in the function, and return the modified value from the function.
===
DEBUG
If the variable is initialized *anywhere* in the function, then Python sees it as local.  Is the code attempting to read this variable before it is assigned?  If so, then perhaps this variable is intended to be a global (and thus was assigned earlier in code execution).  If that's true, then use the 'global' keyword as indicated in the discussion.  
===
DEBUG_STRATEGY
If variable is intended to be a global variable, use the 'global var' statement (where 'var' is your variable) to indicate this to Python.  
=====
ValueError
The code is using an invalid value in a function call, operation or statement.

This error is similar to TypeError (wrong type of object used) but refers to a bad value (wrong value used).  For example int('5') produces an integer with value 5, but int('hello') produces a ValueError exception because Python doesn't know how to translate 'hello' to an integer value.
===
DEBUG
In the error message, you will usually see the operation that was attempted and the object value(s) involved in the operation, along with an explanation of why these value(s) can't be used there (although this may be as simple as "can't do it").

Looking at the error line ({line_no}), find the operation referenced in the message, then attempt to identify the object(s) involved.  You may want to add print statements just above the error line that print the object(s) and their values.  Then look for documentation on the operation or function to see what values are required.  You may need to modify the values of the objects so they can be used here, or you may realize that a different operation or function is needed instead.
===
DEBUG_STRATEGY
Print the value of the object indicated by the error message; review docs or examples for proper usage.  

=====
ZeroDivisionError
The code is attempting to divide by zero, or use zero in a modulus operation.  

Dividing by zero is illegal in most languages, because there is no conventional mathematical result possible.
===
DEBUG_STRATEGY
Print the divisor to verify it is zero; use an 'if' test to make sure it is not zero before dividing.  
===
DEBUG
Looking at the error line, find the division (/) or modulus (%) operation and print the variable that is used as the divisor (the operand, or value, on the right side of the operator) -- it should show as 0.  Decide how this value needs to change so that it is not 0, or perhaps use an 'if' test to avoid the division if the value is sometimes 0.
"""


# 'main body'
# set STDERR to write to a string variable
sys.stderr = io.StringIO()

atexit.register(read_stderr)



