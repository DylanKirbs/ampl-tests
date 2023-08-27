"""
Test Script for AMPL compiler.

Usage:
    test.py (scanner | parser | hashtable | symboltable | typechecking | all) [options] [<tests>...]
    test.py (-h | --help)
    test.py --version

Options:
    -h, --help      Display this help screen
    --version       Show version information
    --verbose       Display verbose output, including debug messages
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
import sys

from docopt import docopt
from termcolor import colored
from pprint import pformat


class CustomFormatter(logging.Formatter):

    COLOURS = {
        logging.DEBUG: lambda s: colored(s, 'blue'),
        logging.INFO: lambda s: colored(s, 'green'),
        logging.WARNING: lambda s: colored(s, 'yellow'),
        logging.ERROR: lambda s: colored(s, 'red'),
        logging.CRITICAL: lambda s: colored(s, 'red', attrs=['bold'])
    }

    def format(self, record):
        colour = self.COLOURS.get(record.levelno, lambda s: s)
        fmt_str = "%(message)s" if record.levelno == logging.INFO else "%(levelname)s:\t%(message)s"

        formatter = logging.Formatter(fmt_str)
        coloured_fmt = colour(formatter.format(record))
        return coloured_fmt


class Test:
    """
    A class representing a test.
    """

    def __init__(
        self,
        executable: str,
        perform_mem_check: bool = True,
        side_by_side: bool = False,
        src_dir=f'{os.getcwd()}/../src',
        bin_dir=f'{os.getcwd()}/../bin',
        tests_dir=f'{os.getcwd()}/tests',
        temp_dir=f'{os.getcwd()}/temp'
    ) -> None:
        """
        Creates a new test.

        :param executable: The name of the executable to test
        :param perform_mem_check: Whether to perform a memory check on the executable
        :param side_by_side: Whether to display the diff side by side
        :param src_dir: The source directory
        :param bin_dir: The binary directory
        :param tests_dir: The tests directory
        :param temp_dir: The temp directory
        """

        # Name
        self._make_name = f'test{executable}'
        self._exe_name = f'test{executable}' if executable != 'parser' else 'amplc'

        # Flags
        self._perform_mem_check = perform_mem_check
        self._side_by_side = side_by_side

        # Directories
        self._src_dir = src_dir
        self._bin_dir = bin_dir
        self._module_dir = executable
        self._temp_dir = temp_dir

        # Constants
        self._TIMEOUT = 10
        self._MEM_TIMEOUT = 20
        self._REDIRECT_TESTS = ['hashtable']

    def compile(self) -> bool:
        """
        Compiles the test.

        Returns:
            bool: True if compilation was successful, False otherwise
        """

        logging.info(f'Compiling {self._module_dir.capitalize()}...')
        clean_proc = subprocess.Popen(
            ['make', 'clean'],
            cwd=self._src_dir,
            stdout=subprocess.DEVNULL
        )
        clean_proc.wait()

        comp_proc = subprocess.Popen(
            ['make', f'{self._make_name}'],
            cwd=self._src_dir,
            stdout=subprocess.DEVNULL
        )
        comp_proc.wait()

        if comp_proc.returncode == 0:
            logging.info(
                f'{self._module_dir.capitalize()} compiled successfully!')
            return True

        logging.error(
            f'{self._module_dir.capitalize()} failed to compile with error code {comp_proc.returncode}')
        return False

    def exec_unit(self, test_number: int) -> bool:
        """
        Executes a single test case.

        :param test_number: The test number to execute
        :return: True if the test executed, False otherwise
        """

        temp_out = f'{self._temp_dir}/{test_number}.out'
        temp_err = f'{self._temp_dir}/{test_number}.err'

        cmd_args = [
            f'{self._bin_dir}/{self._exe_name}',
            f'{self._module_dir}/{test_number}.in'
        ]

        with open(temp_out, 'w') as f_out, open(temp_err, 'w') as f_err:

            if self._module_dir in self._REDIRECT_TESTS:
                cmd_args.pop()
                logging.debug(f'Command: {cmd_args} with input file')
                with open(f'{self._module_dir}/{test_number}.in', 'r') as f_in:
                    process = subprocess.Popen(
                        cmd_args,
                        stdin=f_in,
                        stdout=f_out,
                        stderr=f_err,
                        preexec_fn=os.setsid  # Create a new process group
                    )
            else:
                logging.debug(f'Command: {cmd_args}')
                process = subprocess.Popen(
                    cmd_args,
                    stdout=f_out,
                    stderr=f_err,
                    preexec_fn=os.setsid  # Create a new process group
                )
            logging.debug(f'Process ID: {process.pid}')

            try:
                process.wait(timeout=self._TIMEOUT)
                return True
            except subprocess.TimeoutExpired:
                logging.warning(
                    f'Test {test_number} timed out after {self._TIMEOUT} seconds.')
                self._handle_timeout(process)
                return False

    def memory_check_unit(self, test_number: int) -> bool:

        cmd_args = [
            'valgrind',
            '--leak-check=full',
            '--error-exitcode=255',
            f'{self._bin_dir}/{self._exe_name}',
            f'{self._module_dir}/{test_number}.in'
        ]

        # Check for leaks
        with open(f'{self._temp_dir}/{test_number}.valgrind', 'w') as capture:

            if self._module_dir in self._REDIRECT_TESTS:
                cmd_args.pop()
                logging.debug(f'Valgrind command: {cmd_args} with input file')
                with open(f'{self._module_dir}/{test_number}.in', 'r') as f_in:
                    valgrind_proc = subprocess.Popen(
                        cmd_args,
                        stdin=f_in,
                        stdout=subprocess.PIPE,
                        stderr=capture,
                        preexec_fn=os.setsid  # Create a new process group
                    )
            else:
                logging.debug(f'Valgrind command: {cmd_args}')
                valgrind_proc = subprocess.Popen(
                    cmd_args,
                    stdout=subprocess.PIPE,
                    stderr=capture,
                    preexec_fn=os.setsid  # Create a new process group
                )
            logging.debug(f'Valgrind Process ID: {valgrind_proc.pid}')

        try:
            valgrind_proc.wait(timeout=self._MEM_TIMEOUT)
            if valgrind_proc.returncode == 255:
                logging.error(f'Test {test_number} failed memory check')
                return False
            elif valgrind_proc.returncode != 0:
                logging.warning(
                    "Unable to determine memory check status, execution returned non-zero exit status.")
            return True
        except subprocess.TimeoutExpired:
            logging.warning(
                f'Valgrind {test_number} timed out after {self._MEM_TIMEOUT} seconds.')
            self._handle_timeout(valgrind_proc)
            return False

    def _handle_timeout(self, process: subprocess.Popen):

        logging.debug(f'Terminating process {process.pid}...')

        try:
            # Terminate the whole process group
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            logging.warning(
                f'{self._exe_name} process could not be terminated using SIGTERM, attempting SIGKILL.'
            )
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                logging.error(
                    f'{self._exe_name} process could not be terminated using SIGKILL. Manual intervention required.'
                )
                raise Exception("Test executable could not be terminated.")

    def diff_unit(self, test_number: int) -> bool:
        """
        Does a diff check on the out and err files.

        :param test_number: The test number to diff
        :param flags: The flags to pass to diff
        :return: True if both diffs passed, False otherwise
        """

        diff_flags = '--side-by-side --suppress-common-lines' if self._side_by_side else ''

        passed = True
        for output_type in ['out', 'err']:
            diff_proc = subprocess.Popen(
                [f'diff {diff_flags} {self._temp_dir}/{test_number}.{output_type} {self._module_dir}/{test_number}.{output_type}'],
                shell=True,
                cwd=os.getcwd()
            )
            logging.debug(f'Diff Process ID: {diff_proc.pid}')
            diff_proc.wait()

            if diff_proc.returncode != 0:
                logging.error(
                    f'Test {test_number} failed diff check ({output_type}).')
                passed = False

        return passed

    def test_unit(self, test_number: int) -> bool:
        """
        Runs the test.

        :param test_number: The test number to execute
        :return: True if the test executed, False otherwise
        """

        if not self.exec_unit(test_number):
            return False

        if self._perform_mem_check:
            if not self.memory_check_unit(test_number):
                return False

        if not self.diff_unit(test_number):
            return False

        logging.info(f'Test {test_number} passed.')
        return True

    def run(self, test_cases: list[int]) -> bool:

        if len(test_cases) == 0:
            # count all the .in file in the module directory
            in_files = filter(lambda f: f.endswith(
                '.in'), os.listdir(self._module_dir)
            )
            test_cases = list(map(lambda f: int(f.split('.')[0]), in_files))
            test_cases.sort()

        logging.debug(f'Test cases\n{pformat(test_cases, compact=True)}')

        if not self.compile():
            return False

        passed = []
        for test_number in test_cases:
            if not self.test_unit(test_number):
                passed.append(test_number)

        if len(passed) > 0:
            logging.error(f'Tests {passed} failed.')
            return False

        return True

    def save_results(self, save_dir) -> None:

        if os.path.exists(save_dir):
            shutil.rmtree(save_dir)

        try:
            shutil.move(self._temp_dir, save_dir)
            logging.info(f'Saving test results to {save_dir}...')
        except Exception as e:
            logging.error(f'Error saving test results: {e}')

    def rm_temp(self) -> None:
        """Removes the temp directory."""

        try:
            shutil.rmtree(self._temp_dir)
            logging.info('Temp directory removed successfully.')
        except Exception as e:
            logging.warning(f'Could not remove temp directory: {e}')


def parse_modules(args: dict[str, bool]) -> list[str]:
    """
    Parses the modules from the command line.
    """

    modules = []

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

    if len(modules) == 0:
        logging.error('Invalid modules specified.')
        sys.exit(1)

    logging.debug(f'Modules\n{pformat(modules, compact=True)}')

    return modules


def parse_test_cases(test_args) -> list[int]:
    """
    Parses the test cases from the command line.
    Either a list of integers or a start..end range can be provided.
    """
    cases = []

    if len(test_args) == 0:
        pass
    elif ".." in test_args[0]:
        start, end = map(int, test_args[0].split(".."))
        cases = list(range(start, end + 1))
    else:
        cases = list(map(int, test_args))

    logging.debug(f'Test cases\n{pformat(cases, compact=True)}')
    return cases


def handle_keyboard_interrupt(sig, frame):
    """Handles keyboard interrupts."""

    logging.warning('Keyboard interrupt detected!')
    logging.warning('Ensure that all subprocesses are terminated.')
    sys.exit(0)


def main():

    VERSION = '3.2.0'

    # Interrupt handler
    signal.signal(signal.SIGINT, handle_keyboard_interrupt)

    args = docopt(__doc__, version=f'Version: {VERSION}')
    # Logging setup
    logging.basicConfig(
        level=logging.INFO if not args['--verbose'] else logging.DEBUG,
        format='%(levelname)s:\t%(message)s'
    )
    logging.getLogger().handlers[0].setFormatter(CustomFormatter())

    # Argument parsing
    logging.info(f'Running Test script version {VERSION}')
    logging.debug(f'Arguments\n{pformat(args)}')
    modules = parse_modules(args)
    test_cases = parse_test_cases(args['<tests>'])

    # CWD and temp dir setup
    logging.info('Setting up')
    logging.debug(f'CWD: {os.getcwd()}')
    if ' ' in os.getcwd():
        logging.error('Current working directory should not contain spaces.')
    os.makedirs('temp', exist_ok=True)

    for module in modules:
        logging.info(f'Running {module} tests...')
        test = Test(module, args['--valgrind'], args['--side-by-side'])
        test.run(test_cases)

        if args['--save'] is not None:
            test.save_results(args['--save'])
        else:
            test.rm_temp()

    logging.info('Done.')


if __name__ == '__main__':
    main()
