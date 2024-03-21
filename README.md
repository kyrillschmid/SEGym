# Package DiffPatchSearch

A repo to create patches for a given repository and issue and apply them.

## Installation

To build the project use

```shell script
python -m build
```

in the root directory (i.e., the directory where `pyproject.toml` and
`setup.cfg` live).

After building the package you can install it with pip:

```shell script
pip install dist/diff_patch_search-0.0.1-py3-none-any.whl
```

To install the package so that it can be used for development purposes
install it with

```shell script
pip install -e .
```

in the root directory.

## Working with the project

## Models

Either add a .env file to the root directory with your OpenAI API key:

```
API_KEY=...
```

or to use ollama uncomment the necessary lines in the `call_openai.py` file.

Here I show how to use the tool to create a patch file and apply it to a repository e.g. the [PrimeFactors](https://github.com/kyrillschmid/PrimeFactors.git)

## Python

To create a patch in the PrimeFactors repo, use the following command:

```
diff-patch-search src tests --affected-files  primes.py main_test.py --issue issue.md
```

## Git

To test the patch file, use the following command:

```
git apply --ignore-space-change --ignore-whitespace --verbose patchGPT.patch
```

## Docker

To use docker to apply the patch and run the tests, create a docker image and run it.

```
docker build -t prime_factor_image . 2> output.txt
docker run --name PrimeFactors prime_factor_image
docker cp PrimeFactors:/usr/src/app/test_output.txt ./test_output.txt
```
