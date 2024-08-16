import time
import docker
import tempfile
import logging
import docker.errors
import sys
import stat
import os
import shutil
import io
import subprocess
import xml.etree.ElementTree as ET
import typing
from . import utils
import tarfile

__all__ = ["DockerConnector"]

logger = logging.getLogger(__name__)


class MalformedPatchException(Exception):
    pass


def _parse_pytest_xml(tree: ET.Element) -> dict:
    """
    Parse the XML tree of a pytest test result.

    Args:
        tree (ET.Element): The XML tree of the test results.

    Returns:
        dict: A dictionary containing the test results. The keys are the test names and the values are dictionaries containing the status and the message of the test, if it failed or errored.
    """
    test_results = {}
    for testcase in tree.iter("testcase"):
        test_name = testcase.get("classname") + "." + testcase.get("name")
        test_results[test_name] = {}
        if testcase.find("failure") is not None:
            test_results[test_name]["status"] = "failed"
            test_results[test_name]["message"] = testcase.find("failure").text
        elif testcase.find("error") is not None:
            test_results[test_name]["status"] = "error"
            test_results[test_name]["message"] = testcase.find("error").text
        elif testcase.find("skipped") is not None:
            test_results[test_name]["status"] = "skipped"
            test_results[test_name]["message"] = testcase.find("skipped").text
        else:
            test_results[test_name]["status"] = "passed"
    return test_results


class DockerConnector:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except docker.errors.DockerException:
            print("Docker is not running")
            logger.critical("Docker is not running")
            sys.exit(1)

    @staticmethod
    def _create_dockerfile(temp_dir: str, repo: str, environment_setup_commit: str) -> str:
        all_files = [f for f in os.listdir(os.path.join(temp_dir, "repo"))]
        if "dev-requirements.txt" in all_files:
            install_command = ["RUN pip install -r dev-requirements.txt"]
        elif "requirements.txt" in all_files:
            install_command = ["RUN pip install -r requirements.txt"]
        elif "poetry.lock" in all_files:
            install_command = ["RUN pip install poetry", "RUN poetry install"]
        elif "Pipfile" in all_files:
            install_command = ["RUN pip install pipenv", "RUN pipenv install"]
        elif "setup.py" in all_files:
            install_command = ["RUN pip install . -e"]
        else:
            logger.warning("No requirements file found. Skipping requirements installation.")
            install_command = []
        install_commands = "\n".join(install_command)
        dockerfile_str = f"""
FROM python:3.12-alpine
RUN apk add --no-cache git nano
RUN git clone https://github.com/{repo}.git repo
WORKDIR repo
RUN git checkout {environment_setup_commit}
{install_commands}
RUN pip install pytest
"""
        return dockerfile_str

    def build_image(self, repo: str, environment_setup_commit: str, tag: str):
        """
        Build a docker image for the given repo and commit. First, clone the repo, checkout the commit, and search for a requirements.txt, pipfile, pyproject.toml or poetry.lock file. Then, create a Dockerfile that does the cloning, checkout, and installs the dependencies.
        Then, delete the repo again.

        TODO: move this into a docker container
        """
        temp_dir = tempfile.mkdtemp(prefix=f"se_gym_{tag}_")
        subprocess.run(["git", "clone", f"https://github.com/{repo}.git", "repo"], cwd=temp_dir)
        subprocess.run(
            ["git", "checkout", environment_setup_commit],
            cwd=os.path.join(temp_dir, "repo"),
            check=True,
        )
        dockerfile_str = self._create_dockerfile(temp_dir, repo, environment_setup_commit)
        logger.info(f"Building image {tag} with Dockerfile:\n{dockerfile_str}")
        dockerfile = io.BytesIO(dockerfile_str.encode("utf-8"))
        self.client.images.build(fileobj=dockerfile, tag=tag)

        try:

            def _shutil_onexc(func, path, exc_info):
                """Helper function to remove read-only files on Windows"""
                os.chmod(path, stat.S_IWRITE)
                os.unlink(path)

            shutil.rmtree(temp_dir, onexc=_shutil_onexc)
        except Exception:
            shutil.rmtree(temp_dir)

    def get_base_container(self, repo: str, environment_setup_commit: str):
        """
        Returns the tag of the base container for the given repo and commit.
        """
        logger.debug(f"Setting up repo {repo} at commit {environment_setup_commit}")
        tag = utils.slugify(repo) + "_" + utils.slugify(environment_setup_commit)
        try:
            self.client.images.get(tag)
            logger.info(f"Image {tag} already exists")
        except docker.errors.ImageNotFound:
            logger.info(f"Image {tag} not found. Building image.")
            self.build_image(repo, environment_setup_commit, tag)
        return tag

    def get_child_container(self, repo: str, environment_setup_commit: str):
        tag = self.get_base_container(repo, environment_setup_commit)
        container = self.client.containers.run(
            tag, detach=True, name=f"se_gym_container_{time.time()}_child{tag}", tty=True
        )
        return container

    @staticmethod
    def apply_patch(container: docker.models.containers.Container, patch: str):
        if patch in [None, "", "[]"]:
            logger.info("No patch to apply")
            return ""
        tarstream = io.BytesIO()
        with tarfile.open(fileobj=tarstream, mode="w") as tar:
            tarinfo = tarfile.TarInfo("file.patch")
            tarinfo.size = len(patch.encode("utf-8"))
            tar.addfile(tarinfo, io.BytesIO(patch.encode("utf-8")))
        tarstream.seek(0)
        assert container.put_archive("/repo", tarstream), "Failed to copy patch to container"
        apply_log = container.exec_run(
            "git apply file.patch --ignore-space-change --ignore-whitespace --verbose --recount --inaccurate-eof",
            workdir="/repo",
        )
        if apply_log.exit_code != 0:
            err = f"Failed to apply patch {patch}, error {apply_log.output.decode('utf-8')}"
            logger.info(err)
            raise MalformedPatchException(err)
        return apply_log

    @staticmethod
    def run_tests(
        container: docker.models.containers.Container,
        suite: typing.Literal["pytest"] = "pytest",
    ) -> dict:
        if suite == "pytest":
            command = "pytest --junitxml=testresults.xml"
            _ = container.exec_run(command, workdir="/repo")
            test_xml = container.exec_run("cat testresults.xml", workdir="/repo")
            xml_str = test_xml.output.decode("utf-8")
            tree = ET.fromstring(xml_str)
            result = _parse_pytest_xml(tree)
            return result
        else:
            raise NotImplementedError(f"Suite {suite} not implemented")
