"""
Test Script for AMPL compiler.

Usage:
    test.py (scanner | parser | hashtable | symboltable | typechecking | all) [options] [<tests>...]
    test.py (-h | --help)
    test.py --version

Options:
    -h, --help      Display this help screen
    --version       Show version information
    --side-by-side  Display the differences side by side
    --save=<dir>    Save test output to the specified directory

Examples:
    test.py scanner 1 2 3                       # Run scanner tests 1, 2, 3
    test.py hashtable --side-by-side 0..5       # Run hashtable tests 0 through 5
    test.py symboltable --save=results 0..10    # Run symboltable tests 0 through 10 and save the results to the results directory

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
        module: str,
        test_number: int,
        bin_dir: str,
        test_dir: str = f'{os.getcwd()}/tests',
        timeout: float = 10
) -> bool:
    """
    Executes the test for the specified module and test number.

    :param module: The module to test (testscanner, amplc, testhashtable, testsymboltable)
    :param test_number: The test number to execute
    :param bin_dir: The directory containing the test executables
    :param test_dir: The directory containing the test files (default: tests)
    :param timeout: The timeout in seconds (default: 10)
    :return: True if the test executed, False otherwise
    """

    stdout_path = f'temp/{test_number}.out'
    stderr_path = f'temp/{test_number}.err'

    with open(stdout_path, 'w') as f_out, open(stderr_path, 'w') as f_err:

        process = subprocess.Popen(
            [f'{bin_dir}/{module}', f'{test_dir}/{test_number}.ampl'],
            stdout=f_out,
            stderr=f_err,
            preexec_fn=os.setsid  # Create a new process group
        )

        try:
            process.wait(timeout=timeout)
            return True
        except subprocess.TimeoutExpired:
            cprint(
                f'Test {test_number} timed out after {timeout} seconds.', 'red')
            handle_timeout(process, module)
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


def run_test(
        module: str,
        test_numbers: List[int],
        is_side_by_side: bool = False
) -> bool:
    """
    Runs the tests for the specified module and test numbers.

    :param module: The module to test (scanner, parser, hashtable, symboltable)
    :param test_numbers: The test numbers to execute (default: [0..10])
    :param is_side_by_side: Whether to show side-by-side diff (default: False)
    :return: True if all tests passed, False otherwise
    """

    diff_flags = '--side-by-side --suppress-common-lines' if is_side_by_side else ''

    cprint(f'Running tests for {module}...', 'blue')

    failed_tests = []

    for test_number in test_numbers:

        test_module = f'test{module}' if module != 'parser' else 'amplc'
        res = execute_test(test_module, test_number, f'{os.getcwd()}/../bin')

        if not res:
            failed_tests.append(test_number)
            continue

        passed = True
        for output_type in ['out', 'err']:
            diff_proc = subprocess.Popen(
                [f'diff {diff_flags} temp/{test_number}.{output_type} {module}/{test_number}.{output_type}'],
                shell=True,
                cwd=os.getcwd()
            )
            diff_proc.wait()

            if diff_proc.returncode != 0:
                cprint(f'Test {test_number} failed ({output_type}).', 'red')
                passed = False

        if passed:
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

    if ".." in test_args[0]:
        start, end = map(int, test_args[0].split(".."))
        return list(range(start, end + 1))
    return [int(i) for i in test_args]


def compile_and_run_tests(module, test_cases, side_by_side):
    """Compiles and runs the tests for the specified module."""

    try:
        if compile_test_module(module):
            run_test(module, test_cases, side_by_side)
    except Exception as e:
        cprint(f'Error running tests: {e}', 'red')
        logging.error(f'Error: {e}')
        return False
    return True


def main():
    args = docopt(__doc__)

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
    os.makedirs('temp', exist_ok=True)

    for module in modules:
        if not compile_and_run_tests(module, test_cases, args['--side-by-side']):
            break

    if args['--save'] is not None:
        try:
            shutil.move('temp', args['--save'])
            cprint(f'Test results saved to {args["--save"]}!', 'green')
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
