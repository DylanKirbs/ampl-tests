"""
Utilities for the test module.
"""

import os
import subprocess
import sys

from termcolor import cprint
from enum import Enum

class RedirectedStreams:
    """
    A context manager for redirecting standard streams to files.

    Usage:
    >>> with RedirectedStreams({"out":"temp.out", "err":"temp.err"}, "w") as f:
    >>>     print("Hello, world!", file=f.out)
    >>>     print("Error!", file=f.err)
    """

    def __init__(self, streams=None, mode='w'):
        """
        Initialize the RedirectedStreams context manager.

        :param streams: Dictionary of stream names and file paths.
        :param mode: File mode for opening the files ('w' for write, 'a' for append, etc.).
        """
        if streams is None:
            streams = {}
        self._stream_files = streams
        self._stream_objects = {}
        self._mode = mode

    def __enter__(self):
        """
        Enter the context manager and redirect streams to specified files.
        """
        for stream_name, stream_file in self._stream_files.items():
            try:
                self._stream_objects[stream_name] = open(stream_file, self._mode)
            except OSError as e:
                cprint(f"Error opening {stream_file}: {e}", "red")
                cprint(f"Redirecting {stream_name} to stderr", "yellow")
                self._stream_objects[stream_name] = sys.stderr
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context manager and close the redirected streams.
        """
        for stream in self._stream_objects.values():
            stream.close()

    def __getattr__(self, name):
        """
        Get the file object of the redirected stream by name.
        """
        if name in self._stream_objects:
            return self._stream_objects[name]
        else:
            raise AttributeError(f"'RedirectedStreams' object has no attribute '{name}'")


class LogColours(Enum):
    ERROR = "red"
    WARNING = "yellow"
    POTENTIAL_ERROR = "magenta"

    def __repr__(self):
        return self.name.replace("_", " ")
    
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
    res = subprocess.call(
        [f'make test{module}'],
        shell=True,
        cwd=src,
        stdout=subprocess.DEVNULL
    )

    if res == 0:
        cprint(f'{module.capitalize()} compiled successfully!', 'green')
        return True
    else:
        cprint(f'{module.capitalize()} failed to compile with error code {res}', 'red')
        return False