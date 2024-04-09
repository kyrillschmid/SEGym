import docker
import tempfile
import shutil
import os

def build_image_if_not_exists(tag="python-env"):
    client = docker.from_env()
    try:
        image = client.images.get(tag)
    except docker.errors.ImageNotFound:
        image = client.images.build(path=".", tag="python-env")
    except Exception as e:
        print(e)
        return None
    return image


def run_docker_env(patch=None):

    client = docker.from_env()

    temp_dir = tempfile.mkdtemp()
    
    with open(f'{temp_dir}/file.patch', 'w') as file:
            file.write(patch)
            file.write('\n')

    host_path = temp_dir #'/Users/kyrillschmid/Documents/zenai/Projekte/code/PrimeFactors/patches'
    container_path = '/patches'

    container = client.containers.run(
        "python-env",
        volumes={host_path: {'bind': container_path, 'mode': 'rw'}},
        working_dir="/usr/src/app",
        command="bash -c 'git apply /patches/file.patch --verbose && pytest tests/'",
        detach=True
    )

    # Wait for the container to finish execution
    result = container.wait()

    logs = container.logs().decode('utf-8')
    reward = parse_outputs(logs)

    container.stop()
    container.remove(v={host_path: {'bind': container_path, 'mode': 'rw'}}, force=True)

    return reward


def parse_outputs(logs):
    patch_score = 0
    test_score = 0

    if "Applied patch" in logs and "cleanly" in logs:
        patch_score = 1

    if not "FAILURES" in logs and patch_score == 1:
        test_score = 1

    return patch_score, test_score