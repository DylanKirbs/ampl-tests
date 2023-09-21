"""
Test Script for AMPL compiler.

Usage:
    test.py (scanner | parser | hashtable | symboltable | typechecking | codegen) [options] [<tests>...]
    test.py (-h | --help)
    test.py --version

Options:
    -h, --help          Display this help screen
    --version           Show version information
    --verbose           Display verbose output, including debug messages
    --valgrind          Perform a memory check on the test executables
    --side-by-side      Display the differences side by side
    --save=<dir>        Save test output to the specified directory
    --stream=<stream>   The stream to diff test (out, err, both) [default: both]

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


def process_handler(process: subprocess.Popen, timeout: int) -> int:
    """
    Handles subprocess timeouts.

    :param process: The process to handle
    :param timeout: The timeout in seconds

    :return: The return code of the process or -1 if the process timed out
    """

    try:
        process.wait(timeout=timeout)
        return process.returncode

    # Timeout expired
    except subprocess.TimeoutExpired:
        logging.warning(f'Process timed out after {timeout} seconds.')

        try:
            # Terminate the whole process group
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            logging.warning(
                f'Process could not be terminated using SIGTERM, attempting SIGKILL.'
            )
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                logging.error(
                    f'Process could not be terminated. Manual intervention required.'
                )
                raise Exception("Test executable could not be terminated.")

    return -1


class BaseTest:

    TIMEOUT = 10
    MAKE = 'amplc'
    EXEC = 'amplc'
    DIFF_FILES = ['out', 'err']

    def __init__(
        self,
        test_names: list[str],
        src_dir: str,
        bin_dir: str,
        test_dir: str,
        temp_dir: str,
        results_dir: str = '',
        flags: dict[str, bool] = {
            'side-by-side': False,
            'memory-check': False
        }
    ) -> None:
        """
        Creates a new test.

        :param test_names: The names of the tests to run
        :param src_dir: The source directory
        :param bin_dir: The binary directory
        :param test_dir: The directory containing the tests
        :param temp_dir: The temp (or output) directory
        :param flags: The flags to pass to the test

        Flags:
            side-by-side: Whether to display the diff side by side
        """

        self._test_names = test_names
        self._src_dir = src_dir
        self._bin_dir = bin_dir
        self._test_dir = test_dir
        self._temp_dir = temp_dir
        self._results_dir = results_dir

        self._flags = flags

    def make(self) -> bool:
        """
        Makes the test.

        Returns:
            bool: True if compilation was successful, False otherwise
        """

        clean_proc = subprocess.Popen(
            ['make', 'clean'],
            cwd=self._src_dir,
            stdout=subprocess.DEVNULL
        )
        clean_proc.wait()

        comp_proc = subprocess.Popen(
            ['make', self.MAKE],
            cwd=self._src_dir,
            stdout=subprocess.DEVNULL
        )
        comp_proc.wait()

        if comp_proc.returncode == 0:
            logging.info(
                f'{self.MAKE.capitalize()} compiled successfully!')
            return True

        logging.error(
            f'{self.MAKE.capitalize()} failed to compile with error code {comp_proc.returncode}')
        return False

    def execute(self, test) -> bool:
        """
        Runs the test.

        :param test: The test to execute

        :return: True if the test executed, False otherwise
        """

        cmd_args = [
            f'{self._bin_dir}/{self.EXEC}',
            f'{self._test_dir}/{test}.in'
        ]

        temp_out = f'{self._temp_dir}/{test}.out'
        temp_err = f'{self._temp_dir}/{test}.err'

        with open(temp_out, 'w') as f_out, open(temp_err, 'w') as f_err:

            logging.debug(f'Command: {cmd_args}')
            process = subprocess.Popen(
                cmd_args,
                stdout=f_out,
                stderr=f_err,
                cwd=self._bin_dir,
                preexec_fn=os.setsid  # Create a new process group
            )

            if process_handler(process, self.TIMEOUT) == -1:
                logging.error(f'Execution of {test} timed out.')
                return False

        return True

    def mem_check(self, test) -> bool:
        """
        Perform a memory check.

        :param test: The test to check

        :return: True if the memory check passed, False otherwise
        """

        cmd_args = [
            'valgrind',
            '--leak-check=full',
            '--error-exitcode=255',
            f'{self._bin_dir}/{self.EXEC}',
            f'{self._test_dir}/{test}.in'
        ]

        # Check for leaks
        with open(f'{self._temp_dir}/{test}.valgrind', 'w') as capture:

            logging.debug(f'Valgrind command: {cmd_args}')
            valgrind_proc = subprocess.Popen(
                cmd_args,
                stdout=subprocess.DEVNULL,
                stderr=capture,
                cwd=self._bin_dir,
                preexec_fn=os.setsid  # Create a new process group
            )
            logging.debug(f'Valgrind Process ID: {valgrind_proc.pid}')

            if process_handler(valgrind_proc, self.TIMEOUT) == -1:
                logging.error(f'Memory check of {test} timed out.')
                return False

        return True

    def diff(self, test) -> bool:
        """
        Does a diff check on the out and err files.

        :param test: The test to diff check

        :return: True if both diffs passed, False otherwise
        """

        diff_flags = []

        if self._flags['side-by-side']:
            diff_flags += ['--side-by-side', '--suppress-common-lines']

        passed = True
        for output_type in self.DIFF_FILES:

            cmd_args = [
                'diff',
                f'{self._temp_dir}/{test}.{output_type}',
                f'{self._test_dir}/{test}.{output_type}'
            ]

            if diff_flags:
                cmd_args = cmd_args[:1] + diff_flags + cmd_args[1:]

            logging.debug(f'Diff command for {output_type}: {cmd_args}')
            diff_proc = subprocess.Popen(
                cmd_args,
                cwd=os.getcwd()
            )
            logging.debug(f'Diff Process ID: {diff_proc.pid}')
            diff_proc.wait()

            if diff_proc.returncode != 0:
                logging.error(
                    f'{test}: Failed diff check for {output_type}.')
                passed = False

        return passed

    def clean(self) -> bool:
        """
        Cleans the test, and removes the temp directory.

        Returns:
            bool: True if the test was cleaned, False otherwise
        """

        if not self._results_dir:
            try:
                shutil.rmtree(self._temp_dir)
                logging.info('Temp directory removed successfully.')
            except Exception as e:
                logging.warning(f'Could not remove temp directory: {e}')
                return False
        else:
            # rename
            try:
                shutil.move(self._temp_dir, self._results_dir)
                logging.info('Results saved successfully.')
            except Exception as e:
                logging.warning(f'Could not save results: {e}')
                return False

        return True

    def test(self):
        """
        Runs the tests.
        """

        logging.debug("Making Tester")
        if not self.make():
            logging.error("Failed to Make Tester")
            return

        logging.debug("Executing all tests")
        failed = []
        for test in self._test_names:
            if not self.execute(test):
                logging.error(f"{test}: Failed to execute")
                failed.append(test)
                continue

            if not self.diff(test):
                failed.append(test)

            if self._flags.get('memory-check', False):
                if not self.mem_check(test):
                    logging.error(f"{test}: Failed memory check")
                    failed.append(test) if test not in failed else None

            if test not in failed:
                logging.info(f"{test}: Passed")

        perc = (1-(len(failed)/len(self._test_names))) * 100
        logging.info(f"You passed {round(perc, 2)}% of the tests")

        if failed:
            logging.error(f"Failed tests: {failed}")

        logging.debug("Cleaning up")
        if not self.clean():
            logging.warning("Failed to cleanup")


class RedirectionBaseTest(BaseTest):

    def execute(self, test) -> bool:
        """
        Runs the test.

        Returns:
            bool: True if the test executed, False otherwise
        """

        cmd_args = [
            f'{self._bin_dir}/{self.EXEC}'
        ]

        temp_out = f'{self._temp_dir}/{test}.out'
        temp_err = f'{self._temp_dir}/{test}.err'

        with open(temp_out, 'w') as f_out, open(temp_err, 'w') as f_err:

            logging.debug(f'Command: {cmd_args}')
            logging.debug(f'stdin: {self._test_dir}/{test}.in')
            with open(f'{self._test_dir}/{test}.in', 'r') as f_in:
                process = subprocess.Popen(
                    cmd_args,
                    stdin=f_in,
                    stdout=f_out,
                    stderr=f_err,
                    cwd=self._bin_dir,
                    preexec_fn=os.setsid  # Create a new process group
                )

                if process_handler(process, self.TIMEOUT) == -1:
                    logging.error(f'Execution of {test} timed out.')
                    return False

        return True

    def mem_check(self, test) -> bool:
        """
        Perform a memory check.

        :param test: The test to check

        :return: True if the memory check passed, False otherwise
        """

        cmd_args = [
            'valgrind',
            '--leak-check=full',
            '--error-exitcode=255',
            f'{self._bin_dir}/{self.EXEC}'
        ]

        # Check for leaks
        with open(f'{self._temp_dir}/{test}.valgrind', 'w') as capture:

            logging.debug(f'Valgrind command: {cmd_args}')
            with open(f'{self._test_dir}/{test}.in', 'r') as f_in:
                valgrind_proc = subprocess.Popen(
                    cmd_args,
                    stdout=subprocess.DEVNULL,
                    stdin=f_in,
                    stderr=capture,
                    cwd=self._bin_dir,
                    preexec_fn=os.setsid  # Create a new process group
                )
                logging.debug(f'Valgrind Process ID: {valgrind_proc.pid}')

                if process_handler(valgrind_proc, self.TIMEOUT) == -1:
                    logging.error(f'Memory check of {test} timed out.')
                    return False

        return True


class ScannerTest(BaseTest):

    MAKE = 'testscanner'
    EXEC = 'testscanner'


class ParserTest(BaseTest):

    MAKE = 'testparser'
    EXEC = 'amplc'


class HashtableTest(RedirectionBaseTest):

    MAKE = 'testhashtable'
    EXEC = 'testhashtable'


class SymboltableTest(RedirectionBaseTest):

    MAKE = 'testsymboltable'
    EXEC = 'testsymboltable'


class TypecheckingTest(BaseTest):

    MAKE = 'testtypechecking'
    EXEC = 'amplc'


class CodegenTest(BaseTest):

    MAKE = 'amplc'
    EXEC = 'amplc'

    def execute(self, test) -> bool:
        """
        Runs the test.
        """

        if super().execute(test) != 0:
            return True

        return self.execute_class(test)

    def execute_class(self, test) -> bool:
        """
        Runs the class file.
        """
        cmd_args = [
            'java',
            f'test{test}',
        ]

        temp_out = f'{self._temp_dir}/{test}.class.out'
        temp_err = f'{self._temp_dir}/{test}.class.err'

        logging.info("Executing compiled AMPL file")
        with open(temp_out, 'w') as f_out, open(temp_err, 'w') as f_err:

            logging.debug(f'Command: {cmd_args}')
            with open(f'{self._test_dir}/{test}.class.in', 'r') as f_in:
                process = subprocess.Popen(
                    cmd_args,
                    stdout=f_out,
                    stderr=f_err,
                    stdin=f_in,
                    cwd=self._bin_dir
                    preexec_fn=os.setsid  # Create a new process group
                )

                ret = process_handler(process, self.TIMEOUT)
                logging.debug(f'Process returned {ret}')
                if ret != 0:
                    logging.error(
                        f'Unable to execute {test}.class, execution finished with error code {ret}')
                    return False

        return True


class Tester:
    """
    A class representing a test.
    """

    TESTS = {
        'scanner': ScannerTest,
        'parser': ParserTest,
        'hashtable': HashtableTest,
        'symboltable': SymboltableTest,
        'typechecking': TypecheckingTest,
        'codegen': CodegenTest
    }

    def __init__(
        self,
        executable: str,
        cwd: str = os.getcwd(),
        src_dir: str = '../src',
        bin_dir: str = '../bin',
        result_dir: str = '',
        perform_mem_check: bool = True,
        side_by_side: bool = False,
        stream: str = 'both'
    ) -> None:
        """
        Creates a new test.

        :param executable: The name of the executable to test
        :param perform_mem_check: Whether to perform a memory check on the executable
        :param side_by_side: Whether to display the diff side by side
        :param src_dir: The source directory
        :param bin_dir: The binary directory
        :param tests_dir: The tests directory
        :param result_dir: The directory to save to
        """

        # Name
        self._exec = executable

        if self._exec not in self.TESTS:
            logging.error(f'Invalid executable {self._exec}')
            sys.exit(1)

        # Flags
        self._flags = []
        self._flags.append('memory-check') if perform_mem_check else None
        self._flags.append('side-by-side') if side_by_side else None

        self._diff_stream = []
        self._diff_stream.append('out') if stream in ['out', 'both'] else None
        self._diff_stream.append('err') if stream in ['err', 'both'] else None

        # Directories
        self._src_dir = os.path.join(cwd, src_dir)
        self._bin_dir = os.path.join(cwd, bin_dir)
        self._temp_dir = os.path.join(cwd, 'temp')
        self._results_dir = os.path.join(cwd, result_dir)
        self._test_dir = os.path.join(cwd, executable)

    def run(self, test_cases: list[int]):

        if len(test_cases) == 0:
            # count all the .in file in the module directory
            in_files = filter(lambda f: f.endswith(
                '.in') and "class" not in f, os.listdir(self._exec)
            )
            test_cases = list(map(lambda f: int(f.split('.')[0]), in_files))
            test_cases.sort()

        logging.debug(f'Test cases\n{pformat(test_cases, compact=True)}')

        # Create the test
        test = self.TESTS[self._exec](
            test_cases,
            self._src_dir,
            self._bin_dir,
            self._test_dir,
            self._temp_dir,
            self._results_dir,
            flags={
                'side-by-side': 'side-by-side' in self._flags,
                'memory-check': 'memory-check' in self._flags
            }
        )

        test.DIFF_FILES = self._diff_stream

        # Run the test
        logging.debug(f'Running {self._exec} tests...')
        test.test()


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
    if args['typechecking']:
        modules.append('typechecking')
    if args['codegen']:
        modules.append('codegen')

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

    VERSION = '6.0.0'

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

    # Stream
    stream = 'both'
    if args['--stream'] == 'out':
        logging.info('Testing only stdout...')
        stream = 'out'
    elif args['--stream'] == 'err':
        logging.info('Testing only stderr...')
        stream = 'err'

    # Export jasmin to the ENV
    if 'JASMIN_JAR' not in os.environ:
        logging.info('Exporting jasmin to the environment')

        os.environ['JASMIN_JAR'] = os.path.join(os.getcwd(), 'jasmin.jar')
        logging.debug(f"export JASMIN_JAR={os.environ['JASMIN_JAR']}")

    for exec in modules:
        logging.info(f'Running {exec} tests...')
        test = Tester(
            exec,
            perform_mem_check=args['--valgrind'],
            side_by_side=args['--side-by-side'],
            result_dir=f'{args["--save"]}' if args['--save'] else '',
            stream=stream
        )
        test.run(test_cases)

    logging.info('Done.')


if __name__ == '__main__':
    main()
