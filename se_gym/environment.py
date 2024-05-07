import docker
import tempfile


class Environment:
    def __init__(self):
        self.client = docker.from_env()
        self.build_image_if_not_exists()

    def build_image_if_not_exists(self, tag="python-env"):
        # TODO: rebuild image if changes in repo detected
        try:
            image = self.client.images.get(tag)
        except docker.errors.ImageNotFound:
            image = self.client.images.build(path=".", tag="python-env")
        except Exception as e:
            print(e)
            return None
        return image

    def apply_patch_and_test(self, patch=None):
        temp_dir = tempfile.mkdtemp()

        with open(f"{temp_dir}/file.patch", "w") as file:
            file.write(patch)
            file.write("\n")

        host_path = temp_dir
        container_path = "/patches"

        container = self.client.containers.run(
            "python-env",
            volumes={host_path: {"bind": container_path, "mode": "rw"}},
            working_dir="/usr/src/app",
            command="bash -c 'git apply /patches/file.patch --verbose && pytest tests/'",
            detach=True,
        )

        container.wait()
        logs = container.logs().decode("utf-8")
        container.stop()
        container.remove(
            v={host_path: {"bind": container_path, "mode": "rw"}}, force=True
        )

        reward = parse_outputs(logs)
        return logs, reward


def parse_outputs(logs):
    patch_score = 0
    test_score = 0

    if "Applied patch" in logs and "cleanly" in logs:
        patch_score = 1

    if "FAILURES" not in logs and patch_score == 1:
        test_score = 1

    return patch_score, test_score
