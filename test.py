"""
Test Script for AMPL compiler.

Usage:
    test.py (--scanner | --hashtable | --symboltable | --all) [<tests>...]
    test.py --save=<dir> (--scanner | --hashtable | --symboltable | --all) [<tests>...]
    test.py (-h | --help)
    test.py --version
    
Options:
    -h, --help        Display this help screen
    --version         Show version information
    --scanner         Run scanner test suite
    --hashtable       Run hashtable test suite
    --symboltable     Run symbol table test suite
    --all             Run all test suites
    --save=<dir>      Save test output to the specified directory

Examples:
    test.py --scanner 1 2 3       # Run scanner tests 1, 2, 3
    test.py --hashtable 0..5      # Run hashtable tests 0 through 5
    
There are a total of 30 tests. If no specific tests are provided, tests [0..10] will be executed by default.
The differences will be displayed on the console.

Author: Dylan Kirby - 25853805
Date: 2023-08-13
Version: 1.4
"""
from __future__ import annotations

import os
import subprocess

from docopt import docopt
from termcolor import cprint
from utils import compile_test_module, RedirectedStreams


def execute_test(module, test_number: int, cwd: str = os.getcwd()):

    with RedirectedStreams({"out":f"temp/{test_number}.out", "err":f"temp/{test_number}.err"}, "w") as f:
        subprocess.call(
            [f'../bin/test{module} tests/{test_number}.ampl'],
            shell=True,
            cwd=cwd,
            stdout=f.out,
            stderr=f.err,
            timeout=10 # 10 second timeout
        )

def run_test(module, test_numbers: range | list[int] = range(0, 10+1)):
    """
    Runs the tests for the specified module.
    If no test numbers are specified, tests 0-10 are run by default.

    The results of Diff are output to the console.

    Returns True if all tests pass.
    """

    # Run: bin/{module} tests/{number}.ampl
    # Diff the output with {module}/{number}.out
    # If diff is empty, test passes

    cprint(f'Running tests for {module}...', 'blue')

    failed = []
    for i in test_numbers:
        
        execute_test(module, i)
        
        res_out = subprocess.call(
            [f'diff temp/{i}.out {module}/{i}.out'],
            shell=True,
            cwd=f'{os.getcwd()}'
        )

        res_err = subprocess.call(
            [f'diff temp/{i}.err {module}/{i}.err'],
            shell=True,
            cwd=f'{os.getcwd()}'
        )

        if res_out != 0 or res_err != 0:
            cprint(f'Test {i} failed.', 'red')
            failed.append(i)
        else:
            cprint(f'Test {i} passed.', 'green')

    if len(failed) == 0:
        cprint(f'All tests passed for {module}!', 'green')
        return True
    else:
        cprint(f'Tests {failed} failed for {module}.', 'red')
        return False
        

if __name__ == '__main__':
    args = docopt(__doc__)

    if args['--scanner']:
        module = 'scanner'
    elif args['--hashtable']:
        module = 'hashtable'
    elif args['--symboltable']:
        module = 'symboltable'
    elif args['--all']:
        module = 'all'
    else:
        raise Exception("No module specified.")

    if module == 'all':
        modules = ['scanner', 'hashtable', 'symboltable']
    else:
        modules = [module]

    test_numbers = range(0, 10+1)
    if len(args['<tests>']) != 0:
        temp = args['<tests>']
        if ".." in temp[0]:
            temp = temp[0].split("..")
            test_numbers = range(int(temp[0]), int(temp[1])+1)
        else:
            test_numbers = [int(i) for i in temp]      

    if os.path.exists('temp'):
        subprocess.call(
            ['rm -rf temp'],
            shell=True,
            cwd=f'{os.getcwd()}'
        )
    os.mkdir('temp')


    for module in modules:
        try:
            if compile_test_module(module):
                run_test(module, test_numbers)
        except Exception as e:
            cprint(f'Error: {e}', 'red')
            break

    if args['--save'] is not None:
        subprocess.call(
            [f'mv temp {args["--save"]}'],
            shell=True,
            cwd=f'{os.getcwd()}'
        )
    else:
        subprocess.call(
            ['rm -rf temp'],
            shell=True,
            cwd=f'{os.getcwd()}'
        )
        

