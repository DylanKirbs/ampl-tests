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
    --no-exec-class     Do not execute the compiled AMPL file

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

# ---------------------------------------------------------------------------- #
# Custom formatter


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

# ---------------------------------------------------------------------------- #
# Test Classes


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
    DIFF_FILES = ['out', 'err', 'class.out', 'class.err']

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
            'memory-check': False,
            'exec-class': False,
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

        logging.debug(f"Results dir: {self._results_dir}")
        if self._results_dir == '':
            # remove temp dir
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

        if not super().execute(test):
            return True

        if self._flags.get('exec-class', False):
            return self.execute_class(test)

        return True

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
                    cwd=self._bin_dir,
                    preexec_fn=os.setsid  # Create a new process group
                )

                ret = process_handler(process, self.TIMEOUT)
                logging.debug(f'Process returned {ret}')
                if ret != 0:
                    logging.error(
                        f'Unable to execute {test}.class, execution finished with error code {ret}')
                    return False

        return True

    def clean(self) -> bool:
        success = super().clean()

        # remove the jasmin and class files from bin
        try:
            for file in os.listdir(self._bin_dir):
                if file.endswith((".jasmin", ".class")):
                    os.remove(os.path.join(self._bin_dir, file))

            logging.info('Cleaning bin directory successful.')
        except Exception as e:
            logging.warning(f'Could not remove jasmin and class files: {e}')
            return False

        return success

# ---------------------------------------------------------------------------- #
# Test Runner


TESTS = {
    'scanner': ScannerTest,
    'parser': ParserTest,
    'hashtable': HashtableTest,
    'symboltable': SymboltableTest,
    'typechecking': TypecheckingTest,
    'codegen': CodegenTest
}


def test_runner(
    executable: str,
    test_cases,
    flags,
    cwd: str = os.getcwd(),
    src_dir: str = '../src',
    bin_dir: str = '../bin',
    result_dir: str = '',
    stream: str = 'both'
):
    """
    Creates a new test.

    :param executable: The name of the executable to test
    :param test_cases: The test cases to run
    :param perform_mem_check: Whether to perform a memory check on the executable
    :param side_by_side: Whether to display the diff side by side
    :param src_dir: The source directory
    :param bin_dir: The binary directory
    :param tests_dir: The tests directory
    :param result_dir: The directory to save to
    """

    if executable not in TESTS:
        logging.error(f'Invalid executable {executable}')
        sys.exit(1)

    diff_stream = []
    diff_stream.append('out') if stream in ['out', 'both'] else None
    diff_stream.append('err') if stream in ['err', 'both'] else None
    if flags.get('exec-class', False):
        diff_stream.append('class.out') if stream in ['out', 'both'] else None
        diff_stream.append('class.err') if stream in ['err', 'both'] else None

    if len(test_cases) == 0:
        # count all the .in file in the module directory
        in_files = filter(lambda f: f.endswith(
            '.in') and "class" not in f, os.listdir(executable)
        )
        test_cases = list(map(lambda f: int(f.split('.')[0]), in_files))
        test_cases.sort()

    logging.debug(f'Test cases\n{pformat(test_cases, compact=True)}')

    # Create the test
    test = TESTS[executable](
        test_cases,
        os.path.join(cwd, src_dir),
        os.path.join(cwd, bin_dir),
        os.path.join(cwd, executable),
        os.path.join(cwd, 'temp'),
        result_dir,
        flags
    )
    test.DIFF_FILES = diff_stream

    # Run the test
    logging.debug(f'Running {executable} tests...')
    test.test()

# ---------------------------------------------------------------------------- #
# Argument Parsing and Event Handling


def parse_args(args: dict):
    """
    Parses the modules from the command line.
    """

    modules = []

    for module in TESTS:
        if args[module]:
            modules.append(module)

    if len(modules) == 0:
        logging.error('Invalid modules specified.')
        sys.exit(1)

    logging.debug(f'Modules\n{pformat(modules, compact=True)}')

    cases = []
    test_args = args['<tests>']

    if len(test_args) == 0:
        pass
    elif ".." in test_args[0]:
        start, end = map(int, test_args[0].split(".."))
        cases = list(range(start, end + 1))
    else:
        cases = list(map(int, test_args))

    logging.debug(f'Test cases\n{pformat(cases, compact=True)}')

    return modules, cases


def handle_keyboard_interrupt(sig, frame):
    """Handles keyboard interrupts."""

    logging.warning('Keyboard interrupt detected!')
    logging.warning('Ensure that all subprocesses are terminated.')
    sys.exit(0)

# ---------------------------------------------------------------------------- #


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
    modules, test_cases = parse_args(args)

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

    flags = {
        'side-by-side': args['--side-by-side'],
        'memory-check': args['--valgrind'],
        'exec-class': not args['--no-exec-class']
    }
    logging.debug("Additional Flags: " + pformat(flags))

    for exec in modules:
        logging.info(f'Running {exec} tests...')
        test_runner(
            exec,
            test_cases,
            flags,
            result_dir=args['--save'] if args['--save'] else '',
            stream=stream
        )

    logging.info('Done.')


if __name__ == '__main__':
    main()
