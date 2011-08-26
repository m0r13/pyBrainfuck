#!/usr/bin/env python

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#    
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#    
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Moritz Hilscher"

__license__ = "GPL"
__version__ = "0.9"

import sys
import termios
import tty

# see http://code.activestate.com/recipes/134892/
class Getch:
    @staticmethod
    def getch():
        try:
            return Getch._windows_impl()
        except ImportError:
            try:
                return Getch._unix_impl()     
            except termios.error:
                return sys.stdin.read(1)
            
    @staticmethod
    def _unix_impl():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch
    
    @staticmethod       
    def _windows_impl():
        import msvcrt
        return msvcrt.getch()

class BrainfuckStack:
    """Manages the Brainfuck cells for the interpreter"""
    
    def __init__(self):
        """Constructor"""
        
        self._dict = {}
        
    def get_list(self):
        """Returns a list of all cells"""
        
        return self._dict.values()
        
    def __getitem__(self, index):
        """Returns a cell"""
        
        if not self._dict.has_key(index):
            self._dict[index] = 0
        return self._dict[index]
    
    def __setitem__(self, index, value):  
        """Sets a cell"""
              
        self._dict[index] = value
        
class BrainfuckInterpreter:
    """The Brainfuck interpreter"""
    
    def __init__(self, commands):
        """Constructor"""
        
        self._stack = BrainfuckStack()
        self._stack_position = 0
        self._commands = list(commands)
        self._commands_position = 0
        self._stream_input = None
        self._stream_output = sys.stdout
        self._operators = {">" : self._increment_pointer,
                          "<" : self._decrement_pointer,
                          "+" : self._increment,
                          "-" : self._decrement,
                          "." : self._output,
                          "," : self._input,
                          "[" : self._loop_begin,
                          "]" : self._loop_end}
        
    def _increment_pointer(self):
        """Increments the pointer (Command >)"""
        
        self._stack_position += 1  
    
    def _decrement_pointer(self):
        """Decrements the pointer (Command: <)"""
        
        self._stack_position -= 1
    
    def _increment(self):
        """Increments the current cell (Command: +)"""
        
        self._stack[self._stack_position] += 1
    
    def _decrement(self):
        """Decrements the current cell (Command: -)"""
        
        self._stack[self._stack_position] -= 1
    
    def _output(self):
        """Outputs the current cell (Command: .)"""
        
        self._stream_output.write(chr(self._stack[self._stack_position]))
    
    def _input(self):
        """Reads one char from the input (or stream) into the current cell (Command: ,)"""
        
        if not self._stream_input:
            byte = Getch.getch()
        else:
            byte = self._stream_input.read(1)
        value = 0
        if len(byte) == 1:
            value = ord(byte)
        self._stack[self._stack_position] = value
    
    def _loop_begin(self):
        """A loop begin (Command: [). Jumps to the loop end if cell == 0"""
        
        if self._stack[self._stack_position] != 0:
            return
        found = 0
        for i in range(self._commands_position + 1, len(self._commands)):
            command = self._commands[i]
            if command == "]" and found == 0:
                self._commands_position = i + 1
                return
            elif command == "]":
                found += 1
            elif command == "[":
                found -= 1
    
    def _loop_end(self):
        """A loop begin (Command: ]). Jumps to the loop begin if cell != 0"""
        
        if self._stack[self._stack_position] == 0:
            return
        found = 0
        for i in range(self._commands_position - 1, 0, -1):
            command = self._commands[i]
            if command == "[" and found == 0:
                self._commands_position = i
                return
            elif command == "[":
                found += 1
            elif command == "]":
                found -= 1
                
    def is_end(self):
        """Checks if the run is finished"""
        
        return self._commands_position >= len(self._commands)
    
    def single_step(self):
        """Executes a single step"""
        
        if self.is_end():
            return
        command = self._commands[self._commands_position]
        if not self._operators.has_key(command):
            self._commands_position += 1
            return
        self._operators[command]()
        self._commands_position += 1
        
    def execute(self):
        """Executes the interpreter"""
        
        while not self.is_end(): 
            self.single_step()
            
    def set_command(self, commands):
        """Sets the command. This resets the stack"""
        
        self._commands = list(commands)
        self._commands_position = 0
        self._stack = BrainfuckStack()
        self._stack_position = 0
                
    def set_input_stream(self, stream):
        """Sets the input stream. You can also use a StringIO object"""
        
        self._stream_input = stream
        
    def set_output_stream(self, stream):
        """Sets the output stream. You can also use a StringIO object"""
        
        self._stream_output = stream
        
    def get_output_stream(self):
        """Returns the output stream. If you set as output StringIO object, 
            you can use stream.getvalue() to get the output"""
            
        return self._stream_output
        
    def to_c(self):
        """Converts the brainfuck commands to c code"""
        
        c_commands = {"+" : "++cells[pos];",
                    "-" : "--cells[pos];",
                    ">" : "pos++;",
                    "<" : "pos--;",
                    "." :  "putchar(cells[pos]);",
                    "," : "cells[pos] = getchar();",
                    "[" : "while(cells[pos] != 0) {",
                    "]" : "}"}
        source = "#include <stdio.h>\nint main() {\nint pos = 0;\nchar cells[3000];\n"
        for command in self._commands:
            if not self._operators.has_key(command) or not c_commands.has_key(command):
                continue
            source += c_commands[command]
            source += "\n"
        source += "return 0; }"
        return source
            
if __name__ == "__main__":    
    import optparse
    
    parser = optparse.OptionParser()
    parser.set_usage("Usage: %prog action [options]")
    parser.add_option("-x", "--execute", action="store_true", help="executes the file", default=False, dest="execute")
    parser.add_option("-c", "--compile", action="store_true", help="converts the brainfuck code to c code", default=False, dest="compile")
    parser.add_option("-i", "--input", help="the Brainfuck input file")
    parser.add_option("-o", "--output", help="the c output file")
    options, args = parser.parse_args()
    
    if options.execute and options.compile:
        parser.error("You can only use one action (-x or -c)!")
        sys.exit(-1)
    elif not options.execute and not options.compile:
        parser.error("Please insert a action (-x or -c)!")
        sys.exit(-1)
    
    if not options.input:
        input = sys.stdin.read()
    else:
        f = open(options.input, "r")
        input = f.read()
        f.close()
    
    if not input:
        input = ""
    
    if not options.output:
        output = sys.stdout
    else:
        output = open(options.output, "w")
        
    interpreter = BrainfuckInterpreter(input)
    if options.execute:
        interpreter.execute()        
    elif options.compile:
        output.write(interpreter.to_c())
        if options.input:
            output.close()