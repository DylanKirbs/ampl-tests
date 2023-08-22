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

import os
import re
import sys
from pprint import pprint

from docopt import docopt
from termcolor import cprint

from utils import LogColours as ErrCol
from utils import log_cprint

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


def get_files():
    c_files = []
    for root, dirs, files in os.walk("../src"):
        for file in files:
            if file.endswith(".c"):
                c_files.append(os.path.join(root, file))

    return c_files


def check_file(file):

    with open(file, "r") as f:
        lines = f.readlines()

    if len(lines) < 1:
        log_cprint(ErrCol.WARNING, "empty_file", file, 0, "", "")

    errors = 0
    warnings = 0
    for line_num, line in enumerate(lines):

        # Pre-compute certain checks
        stripped_line = line.strip()
        is_comment = stripped_line.startswith(("/*", "*"), 0, 2)
        string_match = IS_STRING_RE.search(line)
        pointer_match = IS_POINTER_RE.search(line)

        if line.startswith("  ", 0, 4) and not line.startswith(chr(9)):
            rule = "invalid_line_indent_with_spaces"
            log_cprint(ErrCol.ERROR, rule, file, line_num,
                       line.replace('  ', '__'), "__")

        for rule, regex in ERROR_REGEXPS.items():

            if is_comment and rule not in COMMENT_CHECKS:
                continue

            re_match = regex.search(line)
            if not re_match:
                continue

            if pointer_match and rule == "invalid_multiplicative_spacing":
                log_cprint(ErrCol.POTENTIAL_ERROR, rule, file, line_num,
                           stripped_line, re_match.group()) if is_verbose else None
                continue

            if string_match and string_match.start() < re_match.start():
                if rule in COMMENT_CHECKS:
                    log_cprint(ErrCol.ERROR, rule, file, line_num,
                               stripped_line, re_match.group())
                elif is_verbose:
                    log_cprint(ErrCol.POTENTIAL_ERROR, rule, file,
                               line_num, stripped_line, re_match.group())
                continue

            log_cprint(ErrCol.ERROR, rule, file, line_num,
                       stripped_line, re_match.group())
            errors += 1

        for rule, regex in WARNING_REGEXPS.items():

            if is_comment and rule not in COMMENT_CHECKS:
                continue

            re_match = regex.search(line)
            if not re_match:
                continue

            log_cprint(ErrCol.WARNING, rule, file, line_num,
                       stripped_line, re_match.group())
            warnings += 1

    # make sure eof is on a newline
    if lines[-1] == "\n":
        log_cprint(ErrCol.WARNING, "eof_on_newline",
                   file, len(lines), lines[-1].strip())
        errors += 1

    return (errors, warnings)


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

    if total_errors:
        sys.exit(1)

    sys.exit(0)
