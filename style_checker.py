"""
A style checker for C files.
It will automatically scan the `src/` directory, and should be executed from a sibling of `src/`.

Usage:
    style_checker.py [options]
    style_checker.py check [options] <file>...

Options:
    -h, --help      Show this help message and exit
    -v, --verbose   Print verbose output

Examples:
    style_checker.py
    style_checker.py ../src/scanner.c

Author: Dylan Kirby - 25853805
Date: 2023-08-16
Version: 2.0
"""
from __future__ import annotations

import os
import re
import sys
from enum import Enum
from math import exp, floor
from pprint import pprint

from docopt import docopt
from termcolor import cprint


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


def log_cprint(level: LogColours, rule, file_name, line_num, line, match_group=None):
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


# Precompile regexps
ERROR_REGEXPS = {
    # Control Statements
    "control_statement_missing_space": re.compile(r"\b(if|else|for|while|switch|case)\b[:\{\(]"),
    "else_if_missing_space": re.compile(r"elseif"),

    # Operators
    "invalid_multiplicative_spacing": re.compile(r"(([a-z0-9().]+\s+[*/][a-z0-9().]+)|([a-z0-9().]+[*/]\s+[a-z0-9().]+))"),
    "invalid_additive_spacing": re.compile(r"(([a-z0-9().]+\s+[+-][a-z0-9().]+)|([a-z0-9().]+[+-]\s+[a-z0-9().]+))"),
    "preprocessor_not_flush_with_left_margin": re.compile(r"^\s+#"),

    # Delimiters
    "no_space_after_delimiter": re.compile(r"[,;]\w"),
    "more_than_one_statement_per_line": re.compile(r"^(?!for|case);[^;]+;"),

    # Braces
    "paren_with_inner_space": re.compile(r"(\(\s)|(\s\))"),
    "bracket_with_inner_space": re.compile(r"(\[\s)|(\s\])"),
    "paren_and_curly_without_separation": re.compile(r"\)\{"),

    # Function Calls
    "function_with_space": re.compile(r"\b(?!(if|for|while|switch|else|return|void|int|char|double)\b)[a-z]+\s\("),

    # Comments
    "single_line_comment": re.compile(r"//"),

    # Lines
    "line_ends_in_space": re.compile(r"\s\n$"),
    "line_longer_80_chars": re.compile(r"^.{81,}$"),

}

WARNING_REGEXPS = {
    "spaces_in_array_access": re.compile(r"\\w+\[\s*[a-z0-9]+(\s+[+-]\s*)|(\s*[+-]\s+)[a-z0-9]+\s*\]", re.IGNORECASE),
    "violation_of_one_true_brace_style": re.compile(r"\sfor[^\{]*\n"),
    "violation_of_one_true_brace_style": re.compile(r"\swhile[^\{]*\n"),
    "violation_of_one_true_brace_style": re.compile(r"\sif[^\{]*\n"),
    "violation_of_one_true_brace_style": re.compile(r"\selse[^\{]*\n"),
}

COMMENT_CHECKS = [
    "line_longer_80_chars",
    "line_ends_in_space",
    "single_line_comment"
]

IS_STRING_RE = re.compile(r"([\'\"])(.*?)\1")
IS_POINTER_RE = re.compile(
    r"(\b(void|int|char|double|[A-Z]\w+)\s*\*[),]*\s*\w*)")
IS_FUNCTION_DECLARATION_RE = re.compile(
    r"(\b(void|int|char|double|[A-Z]\w+)\s+\w+\s*\(([^;]+)\))[^;]*$")
IS_NON_ASCII = re.compile(r"[^\x00-\x7F]")


def get_files():
    c_files = []
    for root, dirs, files in os.walk("../src"):
        for file in files:
            if file.endswith(".c"):
                c_files.append(os.path.join(root, file))

    return c_files


def check_file(file) -> tuple[int, int]:
    """
    Checks a file for style errors.

    :param file: The file to check
    :return: A tuple of the number of errors and warnings
    """

    with open(file, "r") as f:
        lines = f.readlines()

    if len(lines) < 1:
        log_cprint(LogColours.WARNING, "empty_file", file, 0, "", "")
        return (0, 1)

    errors = 0
    warnings = 0
    for line_num, line in enumerate(lines):

        # Pre-compute certain checks
        stripped_line = line.strip()
        is_comment = stripped_line.startswith(("/*", "*"), 0, 2)
        string_match = IS_STRING_RE.search(line)
        pointer_match = IS_POINTER_RE.search(line)
        function_match = IS_FUNCTION_DECLARATION_RE.search(line)
        non_ascii_match = IS_NON_ASCII.search(line)

        if line.startswith("  ", 0, 4) and not line.startswith(chr(9)):
            rule = "invalid_line_indent_with_spaces"
            errors += 1
            log_cprint(LogColours.ERROR, rule, file, line_num,
                       stripped_line, stripped_line)

        if non_ascii_match:
            rule = "non_ascii_character"
            errors += 1
            log_cprint(LogColours.ERROR, rule, file, line_num,
                       stripped_line, non_ascii_match.group())

        if function_match and line_num > 0:
            prev_line = lines[line_num - 1].strip()
            allowed_prev_line = prev_line == ""
            allowed_prev_line |= "#" in prev_line
            allowed_prev_line |= "//" in prev_line
            allowed_prev_line |= "/*" in prev_line
            allowed_prev_line |= "*/" in prev_line
            if not allowed_prev_line:
                rule = "function_without_empty_line_above"
                errors += 1
                log_cprint(LogColours.ERROR, rule, file,
                           line_num, stripped_line, stripped_line)

        if function_match and not lines[line_num + 1].startswith("{"):
            rule = "function_brace_not_on_line_below_declaration"
            warnings += 1
            log_cprint(LogColours.WARNING, rule, file, line_num,
                       line.replace('  ', '__'), "__")

        for rule, regex in ERROR_REGEXPS.items():

            if is_comment and rule not in COMMENT_CHECKS:
                continue

            re_match = regex.search(line)
            if not re_match:
                continue

            if pointer_match and rule == "invalid_multiplicative_spacing":
                log_cprint(LogColours.POTENTIAL_ERROR, rule, file, line_num,
                           stripped_line, re_match.group()) if is_verbose else None
                continue

            if string_match and string_match.start() < re_match.start():
                if rule not in COMMENT_CHECKS:
                    continue
                elif is_verbose:
                    log_cprint(LogColours.POTENTIAL_ERROR, rule, file,
                               line_num, stripped_line, re_match.group())
                    continue

            log_cprint(LogColours.ERROR, rule, file, line_num,
                       stripped_line, re_match.group())
            errors += 1

        for rule, regex in WARNING_REGEXPS.items():

            if is_comment and rule not in COMMENT_CHECKS:
                continue

            re_match = regex.search(line)
            if not re_match:
                continue

            log_cprint(LogColours.WARNING, rule, file, line_num,
                       stripped_line, re_match.group())
            warnings += 1

    # make sure eof is on a newline
    if lines[-1] == "\n":
        log_cprint(LogColours.WARNING, "eof_on_newline",
                   file, len(lines), lines[-1].strip())
        warnings += 1

    return (errors, warnings)


def score_func(errors, warnings):
    x = floor(errors + warnings/5)
    x /= 10.7

    return floor(100 / exp(x))


if __name__ == "__main__":

    args = docopt(__doc__, version="2.0")
    is_verbose = args["--verbose"]

    cprint("Starting style check", "blue", attrs=["bold"])

    c_files = get_files() if not args["<file>"] else args["<file>"]

    if is_verbose:
        cprint(f"Checking files:", "blue")
        pprint(c_files, indent=4)
        cprint(f"Rules:", "blue")
        pprint(ERROR_REGEXPS, indent=2)
        cprint(f"Warnings:", "blue")
        pprint(WARNING_REGEXPS, indent=2)
        print()

    total_errors = 0
    total_warnings = 0
    for file in c_files:
        e, w = check_file(file)
        total_errors += e
        total_warnings += w

    c = "red" if total_errors else "yellow" if total_warnings else "green"
    cprint(
        f"Check finished with {total_errors} errors and {total_warnings} warnings.", c, attrs=["bold"])

    cprint(
        f"Style Score: {score_func(total_errors, total_warnings)}%", "blue", attrs=["bold"])

    if total_errors:
        sys.exit(1)

    sys.exit(0)
