"""
This modules contains the functions to apply a patch to a codebase and run tests on it.
"""

import time
import docker
import tempfile
import logging
import docker.errors
import sys
import stat
import os
import shutil

DOCKER_TAG = "pytest-env"

logger = logging.getLogger("docker_connector")


class DockerConnector:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except docker.errors.DockerException as e:
            print("Docker is not running")
            logger.critical("Docker is not running")
            sys.exit(1)
        self.build_image_if_not_exists()

    def build_image_if_not_exists(self, tag=DOCKER_TAG):
        try:
            logger.info("Building docker image")
            image = self.client.images.get(tag)
        except docker.errors.ImageNotFound:
            logger.info("Image not found, building new image")
            image = self.client.images.build(path=".", tag=DOCKER_TAG)
        except Exception as e:
            logger.critical("Docker is not running", e)
            sys.exit(1)
        return image

    instance = None

    @staticmethod
    def get_instance():
        if DockerConnector.instance is None:
            DockerConnector.instance = DockerConnector()
        return DockerConnector.instance


class MalformedPatchException(Exception):
    pass


def apply_patch(code_base_root: str, patch: str):
    """
    Apply a patch to a codebase.

    Args:
        code_base_root (str): The root directory of the codebase. The directory will be copied and the patch will be applied to the copy. The original codebase will not be modified. The codebase should be a git repository.
        patch (str): The patch to apply to the codebase. This file might be corrupted, in which case the function will raise an MalformedPatchException.
    """
    # Create a temporary directory to store the codebase
    temp_dir = tempfile.mkdtemp(prefix="se_gym_")
    logger.debug(f"Created temporary directory {temp_dir}")
    # Copy the codebase to the temporary directory
    shutil.copytree(
        src=code_base_root,
        dst=f"{temp_dir}/",
        dirs_exist_ok=True,
    )
    # Write the patch to a file
    with open(f"{temp_dir}/file.patch", "w") as file:
        file.write(patch.strip())
        file.write("\n")
    # Start a container with the codebase
    container = DockerConnector.get_instance().client.containers.run(
        DOCKER_TAG,
        detach=True,
        volumes={temp_dir: {"bind": "/repo", "mode": "rw"}},
        working_dir="/repo",
        # command="/bin/bash",
        tty=True,
        name=f"se_gym_container_{time.time()}",
    )
    # container.wait()
    # Attempt to apply the patch in the container
    apply_log = container.exec_run(
        cmd=[
            "git",
            "apply",
            "--ignore-space-change",
            "--ignore-whitespace",
            "--verbose",
            "--recount",
            "--inaccurate-eof",
            "./file.patch",
        ],
        stdout=True,
        stderr=True,
    )
    print(apply_log)

    # Tear down the container
    # container.wait()
    container.stop()
    container.remove(v={temp_dir: {"bind": "/repo", "mode": "rw"}}, force=True)
    # remove the temporary directory

    def on_rm_error(func, path, exc_info):
        os.chmod(path, stat.S_IWRITE)
        os.unlink(path)

    shutil.rmtree(temp_dir, onexc=on_rm_error)

    # Check if the patch was applied successfully
    if apply_log.exit_code != 0:
        logger.info("Failed to apply patch")
        logger.error(apply_log.output)
        raise MalformedPatchException(
            "Failed to apply patch", apply_log.output.decode("utf-8")
        )
    logger.info("Patch applied successfully")
    print("success")
