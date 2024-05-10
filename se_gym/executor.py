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

GIT_APPLY_PATCH = "git apply --ignore-space-change --ignore-whitespace --verbose --recount --inaccurate-eof ./file.patch"


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


class Container:
    def __init__(self, mount_dir: str):
        self.mount_dir = mount_dir
        self.container = DockerConnector.get_instance().client.containers.run(
            image=DOCKER_TAG,
            detach=True,
            volumes={mount_dir: {"bind": "/repo", "mode": "rw"}},
            working_dir="/repo",
            tty=True,
            name=f"se_gym_container_{time.time()}",
        )

    def run_command(self, command: str):
        return self.container.exec_run(cmd=command, stdout=True, stderr=True)

    def stop(self):
        self.container.stop()
        self.container.remove(
            v={self.mount_dir: {"bind": "/repo", "mode": "rw"}}, force=True
        )


def _shutil_onexc(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    os.unlink(path)


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
    shutil.copytree(src=code_base_root, dst=f"{temp_dir}/", dirs_exist_ok=True)

    with open(f"{temp_dir}/file.patch", "w") as file:
        file.write(patch)  # Write the patch to a file

    container = Container(mount_dir=temp_dir)  # Start a container with the codebase
    apply_log = container.run_command(GIT_APPLY_PATCH)  # Try to patch

    # Tear down the container
    container.stop()

    # remove the temporary directory
    shutil.rmtree(temp_dir, onexc=_shutil_onexc)

    # Check if the patch was applied successfully
    if apply_log.exit_code != 0:
        outp = apply_log.output.decode("utf-8")
        logger.info("Failed to apply patch", outp)
        raise MalformedPatchException("Failed to apply patch", outp)
    logger.info("Patch applied successfully")
