# AMPL Testing Scripts

**WARNING**: The validity of these tests is not guaranteed.

## Repository Structure

The test scripts should be placed along side the `src/` directory of the `AMPL` compiler.

Follow the directory structure below:
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

## Scripts

### Running Tests

The `test.py` script will run the tests, see:
```bash
python3 test.py --help
```

For the purposes of the scanner run:
```bash
# Run all tests
python3 test.py --scanner 0..26
```

### Saving tests to module directory

The `save_tests.sh` script saves the executed code to the module direcory, effectively overwriting the "expected out".

## Contributing

Please fork the repository and checkout a resonable branch name and submit a pull request to merge your changes.

> Do not commit directly to the `master` branch

## Acknowledgments

| Name              | Student Number |
| ----------------- | -------------- |
| Dylan Kirby       | 25853805       |
| Zander Von Ludwig | 25870963       |
| Michael van Zyl   | 22604731       |
