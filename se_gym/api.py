import dataclasses

import os
import random
import typing
import logging
import regex as re
import copy

from . import utils
from . import config
from . import runner_host
from . import runner_docker

random.seed(15)
logger = logging.getLogger("api")
__all__ = ["make"]

if not os.path.exists(config.DEFAULT_SAVE_PATH):
    os.makedirs(config.DEFAULT_SAVE_PATH)


def make(dataset: str = "princeton-nlp/SWE-bench_Lite_oracle/dev"):
    return Environment(get_ds(dataset))


def get_ds(dataset):
    if dataset == "dummy":
        import json

        with open("./dummy_dataset.json", "r") as f:
            return json.load(f)
    else:
        import datasets

        split = None
        if dataset.endswith("/dev") or dataset.endswith("/test"):
            split = dataset.split("/")[-1]
            dataset = "/".join(dataset.split("/")[:-1])
        return datasets.load_dataset(dataset, split=split)


@dataclasses.dataclass
class State:
    repo: typing.Annotated[str, "Repository to be fixed"]
    setup_commit: typing.Annotated[str, "Base commit"]
    path: typing.Annotated[str, "Path to the repository"]
    issue: typing.Annotated[str, "Issue to be fixed"]
    logs: typing.Annotated[typing.Union[str, None], "Logs of previous steps"] = ""
    previous_patches: typing.Annotated[typing.List[str], "Previous patches"] = dataclasses.field(
        default_factory=list
    )
    fail_to_pass: typing.Annotated[typing.List[str], "Tests that currently fails"] = (
        dataclasses.field(default_factory=list)
    )


class InvalidState(State): ...


class Environment:
    def __init__(self, dataset):
        """
        Initialize the environment with a dataset. If the dataset is not available, it will be downloaded lazily.
        """
        self.dataset = dataset
        self.dockerconnector = runner_docker.DockerConnector()
        self.current_index = None
        self.current_path = None
        self.current_issue = None
        self.current_fail_to_pass = None
        self.current_oracle_files = None
        self.current_repo = None
        self.current_commit = None
        self.num_challenges = (  # helper to get the number of issues in the dataset
            self.dataset.num_rows
            if not isinstance(self.dataset, dict)
            else len(self.dataset[list(self.dataset.keys())[0]])
        )

    def reset(self, index: typing.Optional[int] = None) -> State:
        """
        Return a new instance of the selected environment.
        """
        if index is None:
            len_ds = sum(1 for _ in self.dataset["instance_id"])
            index = random.randint(0, len_ds - 1)
        self.current_index = index
        self.current_repo = self.dataset["repo"][self.current_index]
        self.current_issue = self.dataset["problem_statement"][self.current_index]
        self.current_commit = self.dataset["environment_setup_commit"][self.current_index]
        test_patch = self.dataset["test_patch"][self.current_index]

        self.current_path = runner_host.HostEnv.get_environment(
            self.current_repo, self.current_commit
        )
        self.current_fail_to_pass = self._parse_fail_to_pass(
            self.dataset["FAIL_TO_PASS"][self.current_index], self.current_path
        )
        try:
            self.current_oracle_files = self._parse_oracle_text(
                self.dataset["text"][self.current_index]
            )
        except Exception:
            logger.info("No oracle files found", exc_info=True)
            self.current_oracle_files = []
        return State(
            path=self.current_path,
            issue=self.current_issue,
            fail_to_pass=self.current_fail_to_pass,
            previous_patches=[test_patch],
            repo=self.current_repo,
            setup_commit=self.current_commit,
        )

    def step(self, action: typing.Union[str, typing.List[str]], state) -> State:
        """
        Perform an action in the environment.
        """
        if isinstance(action, list):
            return [self.step(a) for a in action]
        if not action:  # Sampler has produced invalid patch
            logger.info("Invalid patch, skipping")
            return InvalidState(**state.__dict__)

        container = self.dockerconnector.get_child_container(
            repo=self.current_repo,
            environment_setup_commit=self.current_commit,
        )
        for patch in state.previous_patches:
            if patch and patch != "[]":
                self.dockerconnector.apply_patch(container, patch=patch)
        self.dockerconnector.apply_patch(container, patch=action)
        log = self.dockerconnector.run_tests(container)
        container.kill()
        new_state = copy.deepcopy(state)
        if new_state.logs:
            new_state.logs.append(log)
        else:
            new_state.logs = [log]

        return new_state

    @staticmethod
    def _parse_oracle_text(text: str) -> typing.List[str]:
        pat = re.compile(r"\[start of (.*?)\]")
        return pat.findall(text)

    @staticmethod
    def _parse_fail_to_pass(fail_to_pass: str, current_path: str) -> typing.List[str]:
        """
        Parse the fail to pass string and return the list of tests that need to be fixed.
        E.g. "['test_boolean_expression_combined (expressions.tests.BasicExpressionsTests)', 'test_boolean_expression_combined_with_empty_Q (expressions.tests.BasicExpressionsTests)']"
        and current_path = "./temp/djangodjango" becomes
        ['temp/djangodjango/tests/expressions/tests.py']
        """
        tests = set()
        for test in eval(fail_to_pass):
            tests.add(
                "/".join(
                    test.split(" ")[-1]
                    .replace("(", "")
                    .replace(")", "")
                    .replace(".", "/")
                    .split("/")[:-1]
                )
                + ".py"
            )
        return [runner_host.find_file(root_dir=current_path, filepath=test) for test in tests]
