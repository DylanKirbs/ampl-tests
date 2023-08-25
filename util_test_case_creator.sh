#!/bin/bash

function cprint {
    # cprint "color" "message"

    case $1 in
        red)    color=31 ;;
        green)  color=32 ;;
        yellow) color=33 ;;
        blue)   color=34 ;;
        purple) color=35 ;;
        cyan)   color=36 ;;
        white)  color=37 ;;
    esac

    echo -e "\033[1;${color}m$2\033[0m"
}

# Validate the arguments
if [ $# < 1 ]; then
    cprint "blue" "$0: Create test cases for a module"
    cprint "yellow" "Usage: $0 <module> <start..stop>"
    exit 1
fi


cprint "blue" "Creating test cases for $1"
python3 test.py --save=save_tests $1 $2 2>&1> /dev/null
if [ $? -ne 0 ]; then
    cprint "red" "Error: Failed to create test cases"
    exit 1
fi

cprint "blue" "Saving test cases to $1/"
mv save_tests/* $1/
if [ $? -ne 0 ]; then
    cprint "red" "Error: Failed to save test cases"
    exit 1
fi

rm -rf save_tests
if [ $? -ne 0 ]; then
    cprint "red" "Error: Failed to remove temporary directory"
    exit 1
fi

cprint "green" "Test cases saved to created successfully"
