from dataclasses import dataclass
import datasets
import os
import random
import typing

from .utils import slugify
from . import config
from . import runner

__dict__ = ["make"]

if not os.path.exists(config.DEFAULT_SAVE_PATH):
    os.makedirs(config.DEFAULT_SAVE_PATH)


def make(dataset: str = "princeton-nlp/SWE-bench_Lite/dev"):
    return Environment(get_ds(dataset))


__dummy_repo = dict(
    repo=["kyrillschmid/PythonEnv"],
    instance_id=["1"],
    base_commit=["aa3a2fd511f550ae77c03c83b545af02ece731fe"],
    problem_statement=[
        "Write a function that takes a string as input and returns the string reversed."
    ],
    environment_setup_commit=["aa3a2fd511f550ae77c03c83b545af02ece731fe"],
)


def get_ds(dataset: str = "princeton-nlp/SWE-bench_Lite/dev"):
    if dataset == "princeton-nlp/SWE-bench_Lite/dev":
        return datasets.load_dataset("princeton-nlp/SWE-bench_Lite", split="dev")
    elif dataset == "princeton-nlp/SWE-bench_Lite/test":
        return datasets.load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    elif dataset == "dummy":
        return __dummy_repo
    else:
        raise ValueError("Invalid dataset name")


def setup_repo(repo: str, environment_setup_commit: str):
    repo_slug = slugify(repo)
    target_path = f"{config.DEFAULT_SAVE_PATH}/{repo_slug}"
    if not os.path.exists(f"{config.DEFAULT_SAVE_PATH}/{repo_slug}"):
        os.system(f"git clone https://github.com/{repo}.git {target_path}")
    os.system(f"cd {target_path} && git checkout {environment_setup_commit}")
    return target_path


@dataclass
class State:
    path: typing.Annotated[str, "Path to the repository"]
    issue: typing.Annotated[str, "Issue to be fixed"]
    logs: typing.Annotated[typing.Union[str, None], "Logs of previous steps"] = None
    fail_to_pass: typing.Annotated[typing.List[str], "Tests that currently fails"] = (
        None
    )


class Environment:
    def __init__(self, dataset: datasets.Dataset):
        """
        Initialize the environment with a dataset. If the dataset is not available, it will be downloaded lazily.
        """
        self.dataset = dataset
        self.current_index = None
        self.current_path = None
        self.current_issue = None
        self.test_patch = None
        self.fail_to_pass = None

    def reset(self):
        """
        Return a new instance of the selected environment.
        """
        len_ds = sum(1 for _ in self.dataset["instance_id"])
        self.current_index = random.randint(0, len_ds - 1)
        self.current_path = setup_repo(
            self.dataset["repo"][self.current_index],
            self.dataset["environment_setup_commit"][self.current_index],
        )
        self.current_issue = self.dataset["problem_statement"][self.current_index]
        self.test_patch = self.dataset["test_patch"][self.current_index]
        self.fail_to_pass = self.parse_fail_to_pass(
            self.dataset["FAIL_TO_PASS"][self.current_index], self.current_path
        )
        return State(
            path=self.current_path,
            issue=self.current_issue,
            fail_to_pass=self.fail_to_pass,
        )

    def step(self, action: typing.Union[str, typing.List[str]]):
        """
        Perform an action in the environment.
        """
        if isinstance(action, list):
            return [self.step(a) for a in action]
        tree = runner.apply_patch_and_test(
            code_base_root=self.current_path, patch=action
        )
        log = runner.parse_pytest_xml(tree)
        return State(
            path=self.current_path,
            issue=self.current_issue,
            logs=log,
            fail_to_pass=self.fail_to_pass,
        )

    @staticmethod
    def parse_fail_to_pass(fail_to_pass: str, current_path: str) -> typing.List[str]:
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
        return [utils.find_file(root_dir=current_path, filename=test) for test in tests]
