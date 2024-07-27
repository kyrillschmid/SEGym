import typing
import logging
import tempfile
import subprocess
import os
from fuzzywuzzy import fuzz
import regex

from . import config
from . import utils

__all__ = ["generate_patch", "find_file", "MalformedPatchException"]

logger = logging.getLogger("runner_host")


class MalformedPatchException(Exception):
    pass


class HostEnv:
    _environments = dict()

    @staticmethod
    def get_environment(repo: str, commit: str):
        key = (repo, commit)
        if key not in HostEnv._environments:
            HostEnv._environments[key] = HostEnv._setup_environment(repo, commit)
        return HostEnv._environments[key]

    @staticmethod
    def cleanup_environment(repo: str, commit: str):
        temp_dir = HostEnv.get_environment(repo, commit)
        subprocess.run(["git", "reset", "--hard", commit], cwd=f"{temp_dir}/repo")

    @staticmethod
    def _setup_environment(repo: str, commit: str):
        temp_dir = tempfile.mkdtemp(prefix=f"se_gym_{utils.slugify(repo)}_{utils.slugify(commit)}_")
        subprocess.run(["git", "clone", f"https://github.com/{repo}.git", "repo"], cwd=temp_dir)
        subprocess.run(["git", "reset", "--hard", commit], cwd=f"{temp_dir}/repo")
        return temp_dir


def find_file(root_dir: str, filepath: str) -> str:
    """
    Find a file in a directory.
    """
    logger.debug(f"Searching for file {filepath} in {root_dir}")
    filepath = os.path.normpath(filepath)
    for dirpatch, _, filenames in os.walk(root_dir):
        for file in filenames:
            if filepath in os.path.join(dirpatch, file):
                # get the relative path from the root dir
                return os.path.relpath(os.path.join(dirpatch, file), root_dir)
    raise FileNotFoundError(f"File {filepath} not found")


def get_code_span(full_code: str, partial_code: str) -> str:
    """
    Get the span of the code in the full code.
    """
    ids_max = str(int(len(partial_code) * config.FUZZY_MATCH_THRESHOLD / 100))
    err = (
        "Old code not found in the file, make sure old_code is exactly the same as in the codebase"
    )

    try:
        match = regex.search(
            "(?b)(" + regex.escape(partial_code) + "){i<=" + ids_max + "}", full_code
        )
    except Exception as e:
        logger.info("Pattern exception", exc_info=True)
        raise ValueError(err)
    if match is None:
        raise ValueError(err)
    else:
        ratio = fuzz.ratio(match.group(), partial_code)
        if ratio < config.FUZZY_MATCH_THRESHOLD:
            logger.info(f"Match ratio below threshold: {ratio}")
            raise ValueError(err)
    return match.span()


def apply_past_patches(
    repo: str,
    environment_setup_commit: str,
    past_patches: typing.List[str],
):
    temp_dir = HostEnv.get_environment(repo, environment_setup_commit)
    for patch in past_patches:
        with open(f"{temp_dir}/file.patch", "w") as f:
            f.write(patch)
        subprocess.run(["git", "apply", "./../file.patch"], cwd=f"{temp_dir}/repo")
    return temp_dir


def generate_patch(
    repo: str,
    environment_setup_commit: str,
    past_patches: typing.List[str],
    filename: str,
    old_code: str,
    new_code: str,
):
    """
    Attempts to generate a valid patch file that changes `old_code` to `new_code` in the repository `repo` at coomit `environment_setup_commit` in file `filename`.
    """
    temp_dir = apply_past_patches(repo, environment_setup_commit, past_patches)
    target_file = find_file(f"{temp_dir}/repo", filename)
    with open(f"{temp_dir}/repo/{target_file}", "r") as f:
        old_file_content = f.read()
    span = get_code_span(old_file_content, old_code)
    new_file_content = old_file_content[: span[0]] + new_code + old_file_content[span[1] :]
    with open(f"{temp_dir}/repo/{target_file}", "w") as f:
        f.write(new_file_content)
    patch = subprocess.run(["git", "diff"], cwd=f"{temp_dir}/repo", capture_output=True)
    if patch.returncode != 0:
        raise MalformedPatchException("Could not generate patch")
    HostEnv.cleanup_environment(repo, environment_setup_commit)
    return patch.stdout.decode()
