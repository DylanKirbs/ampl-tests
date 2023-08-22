"""
Test Script for AMPL compiler.

Usage:
    test.py (scanner | parser | hashtable | symboltable | typechecking | all) [options] [<tests>...]
    test.py (-h | --help)

Options:
    -h, --help      Display this help screen
    --version       Show version information
    --valgrind      Perform a memory check on the test executables
    --side-by-side  Display the differences side by side
    --save=<dir>    Save test output to the specified directory

Examples:
    test.py scanner 1 2 3                       # Run scanner tests 1, 2, 3
    test.py hashtable --side-by-side 0..5       # Run hashtable tests 0 through 5
    test.py symboltable --save=results 0..10    # Run symboltable tests 0 through 10 and save the results to the results directory
    test.py all --valgrind                      # Run all tests with valgrind memory checks

There are a total of 30 tests. If no specific tests are provided, tests [0..10] will be executed by default.
The differences will be displayed on the console.

Author: Dylan Kirby - 25853805
Date: 2023-08-13
"""
from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
from typing import List

from docopt import docopt
from termcolor import cprint

from utils import compile_test_module

# Basic logging configuration
logging.basicConfig(level=logging.INFO)


def execute_test(
        exe_name: str,
        test_number: int,
        bin_dir: str,
        test_dir: str,
        should_valgrind: bool = True,
        timeout: float = 10
) -> bool:
    """
    Executes the test for the specified module and test number.

    :param exe_name: The name of the module's binary file (testscanner, amplc, testhashtable, testsymboltable)
    :param test_number: The test number to execute
    :param bin_dir: The directory containing the test executables
    :param test_dir: The directory containing the test files
    :param should_valgrind: Whether to perform a memory check (default: True)
    :param timeout: The timeout in seconds (default: 10)

    :return: True if the test executed, False otherwise
    """

    stdout_path = f'temp/{test_number}.out'
    stderr_path = f'temp/{test_number}.err'

    with open(stdout_path, 'w') as f_out, open(stderr_path, 'w') as f_err:

        process = subprocess.Popen(
            [f'{bin_dir}/{exe_name}', f'{test_dir}/{test_number}.ampl'],
            stdout=f_out,
            stderr=f_err,
            preexec_fn=os.setsid  # Create a new process group
        )

        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            cprint(
                f'Test {test_number} timed out after {timeout} seconds.', 'red')
            handle_timeout(process, exe_name)
            return False

    if not should_valgrind:
        return True

    # Check for leaks
    valgrind_proc = subprocess.Popen(
        ['valgrind', '--leak-check=full', '--error-exitcode=-1',
            f'{bin_dir}/{exe_name}', f'{test_dir}/{test_number}.ampl'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid  # Create a new process group
    )

    try:
        valgrind_proc.wait(timeout=timeout)
        if valgrind_proc.returncode == -1:
            cprint(f'Test {test_number} failed memory check', 'red')
            return False
        return True
    except subprocess.TimeoutExpired:
        cprint(
            f'Valgrind {test_number} timed out after {timeout} seconds.', 'red')
        handle_timeout(valgrind_proc, exe_name)
        return False


def handle_timeout(process: subprocess.Popen, module: str):

    try:
        # Terminate the whole process group
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        logging.warning(
            f'{module} process could not be terminated using SIGTERM, attempting SIGKILL.'
        )
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            logging.error(
                f'{module} process could not be terminated using SIGKILL. Manual intervention required.'
            )
            raise Exception("Test executable could not be terminated.")


def diff_check(module: str, test_number: int, flags: str = '') -> bool:
    """
    Does a diff check on the out and err files.

    :param module: The module to diff the output files on
    :param test_number: The test number to diff
    :param flags: The diff check flags
    :return: True if both diffs passed, False otherwise
    """

    passed = True
    for output_type in ['out', 'err']:
        diff_proc = subprocess.Popen(
            [f'diff {flags} temp/{test_number}.{output_type} {module}/{test_number}.{output_type}'],
            shell=True,
            cwd=os.getcwd()
        )
        diff_proc.wait()

        if diff_proc.returncode != 0:
            cprint(f'Test {test_number} failed ({output_type}).', 'red')
            passed = False

    return passed


def run_test(
        module: str,
        test_numbers: List[int],
        is_mem_check: bool = True,
        is_side_by_side: bool = False
) -> bool:
    """
    Runs the tests for the specified module and test numbers.

    :param module: The module to test (scanner, parser, hashtable, symboltable)
    :param test_numbers: The test numbers to execute (default: [0..10])
    :param is_mem_check: Whether to perform a memory check (default: True)
    :param is_side_by_side: Whether to show side-by-side diff (default: False)

    :return: True if all tests passed, False otherwise
    """

    diff_flags = '--side-by-side --suppress-common-lines' if is_side_by_side else ''

    # Get the bin and test directories
    bin_dir = os.path.join(os.getcwd(), '../bin')
    test_dir = os.path.join(os.getcwd(), 'tests')

    cprint(f'Running tests for {module}...', 'blue')

    failed_tests = []

    for test_number in test_numbers:

        module_name = f'test{module}' if module != 'parser' else 'amplc'

        if not execute_test(module_name, test_number, bin_dir,  test_dir, is_mem_check):
            failed_tests.append(test_number)
            continue

        if diff_check(module, test_number, diff_flags):
            cprint(f'Test {test_number} passed.', 'green')
        else:
            failed_tests.append(test_number)

    if not failed_tests:
        cprint(f'All tests passed for {module}!', 'green')
        return True

    cprint(f'Tests {failed_tests} failed for {module}.', 'red')
    return False


def rm_temp():
    """Removes the temp directory."""

    temp_dir = os.path.join(os.getcwd(), 'temp')

    try:
        shutil.rmtree(temp_dir)
        cprint('Temp directory removed successfully.', 'green')
    except Exception as e:
        cprint(f'Warning: Could not remove temp directory: {e}', 'yellow')
        cprint(
            'The temp directory may contain .nfs files, this is expected behavior.', 'yellow')


def parse_test_cases(test_args):
    """
    Parses the test cases from the command line.
    Either a list of integers or a start..end range can be provided.
    """

    if not test_args:
        # get all the available tests
        count = len(os.listdir(os.path.join(os.getcwd(), 'tests')))
        return list(range(0, count + 1))

    if ".." in test_args[0]:
        start, end = map(int, test_args[0].split(".."))
        return list(range(start, end + 1))
    return [int(i) for i in test_args]


def compile_and_run_tests(module, test_cases, is_mem_check, side_by_side):
    """Compiles and runs the tests for the specified module."""

    try:
        if compile_test_module(module):
            run_test(module, test_cases, is_mem_check, side_by_side)
    except Exception as e:
        cprint(f'Error running tests: {e}', 'red')
        logging.error(f'Error: {e}')
        return False
    return True


def handle_keyboard_interrupt(sig, frame):
    """Handles keyboard interrupts."""

    cprint('Keyboard interrupt detected, cleaning up...', 'yellow')
    cprint('Warning: Please kill any lingering test executables manually.', 'red')
    rm_temp()
    exit(0)


def main():

    signal.signal(signal.SIGINT, handle_keyboard_interrupt)

    args = docopt(__doc__)
    test_dir = os.getcwd()

    modules = []
    test_cases = range(0, 50+1)

    if args['scanner']:
        modules.append('scanner')
    if args['parser']:
        modules.append('parser')
    if args['hashtable']:
        modules.append('hashtable')
    if args['symboltable']:
        modules.append('symboltable')
    if args['all']:
        modules = ['scanner', 'parser', 'hashtable', 'symboltable']

    test_cases = parse_test_cases(args['<tests>'])

    if len(modules) == 0:
        cprint('Invalid modules specified.', 'red')
        return

    cprint('Executing Setup', 'yellow')
    os.chdir(test_dir)
    os.makedirs('temp', exist_ok=True)

    for module in modules:
        if not compile_and_run_tests(module, test_cases, args['--valgrind'], args['--side-by-side']):
            break

    os.chdir(test_dir)
    if args['--save'] is not None:

        if os.path.exists(args['--save']):
            shutil.rmtree(args['--save'])

        try:
            shutil.move('temp', args['--save'])
            cprint(
                f'Test results saved to {args["--save"]} directory!', 'green')
            logging.info(f'Saving test results to {args["--save"]}...')
        except Exception as e:
            cprint(f'Error saving test results: {e}', 'red')
            logging.error(f'Error saving test results: {e}')
    else:
        cprint('Cleaning up...', 'yellow')
        rm_temp()

    cprint('Done.', 'blue')


if __name__ == '__main__':
    main()
