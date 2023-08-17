"""
Utilities for the test module.
"""

import os
from subprocess import Popen, DEVNULL

from termcolor import cprint
from enum import Enum


class LogColours(Enum):
    ERROR = "red"
    WARNING = "yellow"
    POTENTIAL_ERROR = "magenta"

    def __repr__(self):
        return self.name.replace("_", " ")
    
    def __str__(self):
        return self.__repr__()
    
    def color(self):
        return self.value
    
def log_cprint(level:LogColours, rule, file_name, line_num, line, match_group=None):
    """
    Prints an error message to the console.
    :param level: The level of the error
    :param rule: The rule that was broken
    :param file_name: The name of the file that the error occured in
    :param line_num: The line number that the error occured on
    :param line: The line that the error occured on
    """

    if match_group:
        line = line.replace(match_group, f"\033[1m{match_group}\033[0m")

    cprint(f"{level}: <{rule}> on line {line_num + 1} of {file_name}", level.color())
    print(">", line)
    print()

def compile_test_module(module, src = f'{os.getcwd()}/../src') -> bool:
    """
    Compiles the specified module and returns True if successful.
    Runs the command `make test{module}` in the src directory.
    """

    cprint(f'Compiling {module}...', 'blue')
    clean_prco = Popen(
        [f'make clean'],
        shell=True,
        cwd=src,
        stdout=DEVNULL
    )
    clean_prco.wait()
    comp_proc = Popen(
        [f'make test{module}'],
        shell=True,
        cwd=src,
        stdout=DEVNULL
    )
    comp_proc.wait()

    if comp_proc.returncode == 0:
        cprint(f'{module.capitalize()} compiled successfully!', 'green')
        return True
    else:
        cprint(f'{module.capitalize()} failed to compile with error code {comp_proc}', 'red')
        return False