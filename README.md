# SEGym

SEGym allows you to apply patches to Python packages and run tests in isolated environments.
This allows you to automatically search for patches with some solver (e.g. with an LLM) until all tests are resolved.

## Prerequisites

Docker installed and running

## Installation

To build the project use

```shell script
python -m build
```

in the root directory (i.e., the directory where `pyproject.toml` and
`setup.cfg` live).

After building the package you can install it with pip:

```shell script
pip install dist/se_gym-0.0.1-py3-none-any.whl
```

To install the package so that it can be used for development purposes
install it with

```shell script
pip install -e .
```

in the root directory.

## Working with the project

## Models

To use a standard one shot solver (GPT-4, Mistral, ...) add a .env file to the root directory with your API key:

```
API_KEY=...
```

see the notes for other APIs (ollama).

## Python

After installing the package you can apply your solver to some repo with an open issue.
For that within the root directory of the repository use the following command:

To create a patch in the PrimeFactors repo, use the following command:

```
se-gym --affected-files primes.py main_test.py --issue issue.md
```

The standard solver assumes that your repo contains a src and tests directory. For the standard
solver you can specify which files are affected by that issue. Also pass the file where the issue
is described.

This command will create a docker image where your python package will be installed. For each generated patch
a new docker container will be created, the patch applied and the tests will be executed.

There are three possible outcomes which reflect how successful the patch is:

1. Patch not applicable, tests fail : (0, 0)
2. Patch applicable, tests fail : (1, 0)
3. Patch applicable, all tests succeed (1, 1)

## Apply patch

he standard solver will create a directory `patches` where the generated patch is placed.

To test the patch file, use the following command:

```
git apply --ignore-space-change --ignore-whitespace --verbose patchGPT.patch
```

## Docker

If you have a Docker related issues with the mounted volume on Mac, the following command might fix it:

```
sudo ln -s "$HOME/.docker/run/docker.sock" /var/run/docker.sock
```
