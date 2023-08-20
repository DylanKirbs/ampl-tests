# AMPL Testing Scripts

![Header Image](https://repository-images.githubusercontent.com/678396879/33ab37e9-c433-4848-b67a-8f535c5bcb8c)

Welcome to the AMPL Testing Scripts repository! This repository contains a set of testing scripts designed to ensure the quality and functionality of the AMPL compiler. Please note that while we strive to maintain accurate tests, the validity of these tests is not guaranteed.

## Overview

This repository houses a collection of testing scripts tailored to the AMPL compiler. By following the setup and usage guidelines outlined below, you can seamlessly run tests, check coding style, and even automate code formatting.

## Setup

### Repository Structure

To best utilize these testing scripts, adhere to the following directory structure:

```
ampl/
    src/
        test{module}.c
        {requirements}.c
        {requirements}.h
        Makefile
    test/
        test.py
        tests/
            0.ampl
            ...
        {module}/
            0.out
            ...
    bin/
        test{module}
```

### Seamless Integration and Updates

For optimal integration, we recommend cloning this repository directly into your existing `ampl/` directory where your AMPL compiler is located. By doing so, you will be able to effortlessly keep your test suite up-to-date with the latest advancements through a simple `git pull` command.

Here's how you can set it up:

1. **Initial Setup:**
    Open your terminal and navigate to the root directory of your AMPL compiler (`ampl/`). Then, execute the following commands:

    ```bash
    cd ampl
    git clone https://github.com/DylanKirbs/ampl-tests test
    ```

    This will clone the repository and create a `test` directory within your AMPL directory.

2. **Keeping Up-to-Date:**
    As new versions of the test suite are released, you can effortlessly update your local copy by using the following commands:

    ```bash
    cd ampl/test
    git pull
    ```

    Running these commands while inside the `test` directory will pull the latest changes from the repository.

Please note, when performing actions related to your AMPL version control, remember to operate from the `ampl/` directory rather than the `test/` directory to ensure smooth integration.

By adhering to this approach, you can seamlessly maintain and utilize the latest test suite advancements while working with your AMPL compiler.

### Requirements

Before proceeding, ensure your system meets the following requirements:

- [Python 3](https://www.python.org/)
- [GCC](https://gcc.gnu.org/)
- [Make](https://www.gnu.org/software/make/)

You can install these dependencies using the following command:

```bash
sudo apt install gcc make python3 python3-pip
```

Additionally, install the required Python packages by running:

```bash
cd ampl/test
python3 -m pip install -r requirements.txt
```

## Usage

All test scripts should be executed from the `test/` directory.

### Running Tests

Execute the `test.py` script to initiate tests. To explore available options, run:

```bash
python3 test.py --help
```

For example, to run scanner tests:

```bash
# Run scanner tests 0 through 30
python3 test.py scanner 0..30
# Run scanner tests 5 8 19 and 27
python3 test.py scanner 5 8 19 27
# Side by side comparison of scanner tests 0 and 1
python3 test.py scanner --side-by-side 0 1 
```

```bash
# See the diff manual
man diff
# or
info diff
```

> **NOTE** <br>
> The parser tests require you to enable the debug flags in the Makefile. To do so, open the Makefile and uncomment the following, in the compiler flags section:
> ```Makefile
> DFLAGS = # -DDEBUG_PARSER ...
> ```
> You must also ensure that all of your `parse_` methods have the appropriate `DBG_` calls. For example:
> ```c
> void parse_program(void)
> {
>     DBG_start("<program>");
>     ...
>     DBG_end("</program>");
> }
> ```
> The tests can then be executed using the script as normal.

### Style Checking

To maintain consistent coding style, you can utilize two style checking scripts: `styletest.py` and `style_checker.py`. For the latest and more comprehensive checks, use `style_checker.py`. Both scripts can be run as follows:

```bash
python3 styletest.py
python3 style_checker.py
```

### Auto-Formatting with clang-format

For code auto-formatting using `clang-format`, follow these steps:

1. Install Clang-Format version 16 and add it to your PATH:

```bash
python3 -m pip install clang-format==16.0.6 && echo 'export PATH="$PATH'":$(python3 -m site --user-base)/bin\"" >> ~/.bashrc
source ~/.bashrc
```

2. Copy the `.clang-format` file to the root of the project.

```bash
cp .clang-format ..
```

3. Format your code using:

```bash
clang-format -i src/*.c
```

**Note**: Be cautious, as auto-formatting may alter your code style. Always review changes using `git diff` before committing.

### Creating Tests for a Module

If you're contributing to the test suite, utilize the `create_test_cases.sh` script. This script saves executed code to the module directory, effectively overwriting the "expected out."

## Contributing

We welcome contributions to this project! To get started, fork the repository, create a meaningful branch, and submit a pull request. Please avoid committing directly to the `master` branch.

## Acknowledgments

| Name              | Student Number |
| ----------------- | -------------- |
| Dylan Kirby       | 25853805       |
| Zander Von Ludwig | 25870963       |
| Michael van Zyl   | 22604731       |
| Matthew Stein     | 25400800       |
| Louis Wilkinson   | 25948873       |
| Luke Leppan       | 25849611       |

Your contributions make this project possible!
