import docker
import tempfile
import os
import shutil
import subprocess

DOCKER_TAG = "pytest-env"


class Environment:
    def __init__(self, base_dir=None):
        self.client = docker.from_env()
        self.build_image_if_not_exists()
        if base_dir is None:
            base_dir = os.getcwd()
        self.base_dir = base_dir

    def build_image_if_not_exists(self, tag=DOCKER_TAG):
        try:
            image = self.client.images.get(tag)
        except docker.errors.ImageNotFound:
            image = self.client.images.build(path=".", tag=DOCKER_TAG)
        except Exception as e:
            print(e)
            return None
        return image

    def apply_patch_and_test(self, patch: str, command: str = "pytest"):
        temp_dir = tempfile.mkdtemp()
        shutil.copytree(
            src=self.base_dir,
            dst=f"{temp_dir}/repo",
        )
        with open(f"{temp_dir}/file.patch", "w") as file:
            file.write(patch)
            file.write("\n")

        try:
            apply_log = subprocess.run(
                [
                    "git",
                    "apply",
                    "--ignore-space-change",
                    "--ignore-whitespace",
                    "--verbose",
                    "./../file.patch",
                ],
                cwd=f"{temp_dir}/repo",
                capture_output=True,
                text=True,
            )
        except Exception as e:
            return "", [0, 0]
        if apply_log.returncode != 0:
            return "", [0, 0]

        container = self.client.containers.run(
            DOCKER_TAG,
            volumes={f"{temp_dir}/repo": {"bind": "/usr/app", "mode": "rw"}},
            working_dir="/usr/app",
            command=command,
            detach=True,
        )

        container.wait()
        logs = container.logs().decode("utf-8")
        container.stop()
        container.remove(
            v={f"{temp_dir}/repo": {"bind": "/usr/app", "mode": "rw"}}, force=True
        )
        if "FAILURES" not in logs:
            return logs, [1, 1]
        else:
            return logs, [1, 0]
