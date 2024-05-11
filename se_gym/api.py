from dataclasses import dataclass
import datasets
import os
import random
import typing

from .utils import slugify
from . import config

__dict__ = ["make"]

if not os.path.exists(config.DEFAULT_SAVE_PATH):
    os.makedirs(config.DEFAULT_SAVE_PATH)


def make(dataset: str = "princeton-nlp/SWE-bench_Lite/dev"):
    return Environment(get_ds(dataset))


def get_ds(dataset: str = "princeton-nlp/SWE-bench_Lite/dev"):
    if dataset == "princeton-nlp/SWE-bench_Lite/dev":
        return datasets.load_dataset("princeton-nlp/SWE-bench_Lite", split="dev")
    elif dataset == "princeton-nlp/SWE-bench_Lite/test":
        return datasets.load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    elif dataset == "princeton-nlp/SWE-bench_Lite/devtiny":
        return datasets.load_dataset("princeton-nlp/SWE-bench_Lite", split="dev")[5:7]
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


class Environment:
    def __init__(self, dataset: datasets.Dataset):
        self.dataset = dataset
        self.current_index = None
        self.current_path = None
        self.current_issue = None

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
        return State(self.current_path, self.current_issue)
