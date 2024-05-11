# SEGym

# THIS IS A WORK IN PROGRESS FORK OF THE ORIGINAL REPO
## TODO
- [ ] Restore script entry point
- [ ] Restore original README and script
- [ ] Log incorrectly generated patches instead of just fixing them 
- [ ] Make entire docker container generation async to always have a container ready
- [x] Integrate https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite
- [ ] Integrate into W&B for logging
- [ ] Automatically read `devcontainer.json`, `.github/workflows`, ... to determine test commands and environment


SEGym allows you to simulate patches for Python repos in isolated environments.
You can use such an environment to let a solver (e.g. LLM) search for a patch for a given issue until the issue is resolved.



## Prerequisites

Docker installed and running. `poetry` installed.
Setup python environment using `poetry install`

## Installation

Currently only usable as a module, not as a script.

## Working with the project

### Models

Supply your own `openai.Client` compatible API.

FOR LMU: use `openai_lmu.get_lmu_openai_client()` to get a ready-to-use client.

### Python

After installing the package you can apply your solver to a repo with an open issue.
Your repo needs to be pip installable! You can use this [PythonEnv](https://github.com/kyrillschmid/PythonEnv.git) as a template for your Python package!





To create a patch in a repo, navigate to the root directory and use the following command:

<!-- ```
se-gym --affected-files file-1.py file-2.py --issue issue.md
``` -->
(Download test files using `pytest se_gym`. Tests sometimes fail due to stochastic nature of the models.)
```
python main.py --base-dir ./temp/barcode --api ollama_lmu --issue ./temp/barcode_issue.md --model "llama3:latest" 
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

### Docker
If you have a Docker related issues with the mounted volume on Mac, the following command might fix it: `sudo ln -s "$HOME/.docker/run/docker.sock" /var/run/docker.sock`
