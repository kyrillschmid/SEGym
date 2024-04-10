# SEGym

SEGym allows you to apply patches to Python packages and run tests in isolated environments.
You can use such an environment to let a solver (e.g. LLM) search for a patch for a given issue until all tests are passed.

Here is the main loop to be used by any solver:

```python
solver = Solver(args)
    env = Environment()

    api = 'openai' # 'openai' , 'ollama_lmu', 'ollama_local', 'groq'
    model = 'gpt-4-0125-preview' # gpt-4-0125-preview, mistral, mixtral-8x7b-32768
    last_patch = None
    feedback = None

    for i in range(1):
        patch = solver.generate_patch(i, args.issue, api, model, last_patch, feedback)
        logs, result = env.apply_patch_and_test(patch)
        last_patch = patch
        feedback = logs
        if result[0] == 1 and result[1] == 1:
            break
```

## Prerequisites

Docker installed and running

Create virtualenv:

```
python3 -m venv ~/.se_gym
source ~/.se_gym/bin/activate
pip install -r requirements.txt
```

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

After installing the package you can apply your solver to a repo with an open issue.
Your repo needs to be pip installable! You can use this [PythonEnv](https://github.com/kyrillschmid/PythonEnv.git) as a template for your Python package!

To create a patch in a repo, navigate to the root directory and use the following command:

```
se-gym --affected-files file-1.py file-2.py --issue issue.md
```

The standard solver assumes that your repo contains a `src` and `tests` directory. For the standard
solver you can specify which files are affected by that issue. Also pass the file where the issue
is described.

This command will create a docker image where your python package will be installed. For each generated patch
a new docker container will be created, the patch applied and the tests will be executed.

There are three possible outcomes which reflect how successful the patch is:

1. Patch not applicable : (0, 0)
2. Patch applicable, tests fail : (1, 0)
3. Patch applicable, all tests succeed (1, 1)

## Apply patch

The standard solver will put the patches in a corresponding model directory.
To test the patch file, use the following command:

```
git apply --ignore-space-change --ignore-whitespace --verbose gpt-4-0125-preview/create_patch_string.patch
```

Install your repo in dev mode:

```
pip install -e .
```

Run tests:

```
pytest
```

## Docker

If you have a Docker related issues with the mounted volume on Mac, the following command might fix it:

```
sudo ln -s "$HOME/.docker/run/docker.sock" /var/run/docker.sock
```
