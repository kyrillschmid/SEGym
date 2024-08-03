import subprocess

from haystack.components.builders import PromptBuilder
from haystack.document_stores.in_memory import InMemoryDocumentStore
import haystack
import copy
import dataclasses
import typing
import logging
import ast
import re

logger = logging.getLogger("codemapobserver")

__all__ = ["CodeMapRetriever"]


@dataclasses.dataclass
class SummarizedFile:
    relative_path: str
    content: str
    summary: str = ""


@dataclasses.dataclass
class SummarizedDirectory:
    relative_path: str
    children: typing.List[typing.Union["SummarizedDirectory", SummarizedFile]]
    summary: str = ""


class Summarizer:
    TEMPLATE_SUMFILE = """You are a world-class software engineer. You have been tasked to create a full code map of a repository by crawling it bottom to top. Summarize the following file in two or three sentences, containing the most important information in the file. Write only about the most relevant functions, methods and classes. Do not violate the length constraint. Mention important classes and methods using `backticks`, but do not use ```codeblocks```. 
    If the file is empty, respond with "This file is empty.", else respond with "In this file, ...".
    Do not mention your own name or the name of the file in the response, only summarize the content of the file.
    Do not apologize for the length of the response or mention that the response is short.
    If the file does not contain code but other content, still summarize the content of the file.


    The filepath is {{filetosummarize.relative_path}} 
    The filecontent is:
```
{{filetosummarize.content}}
```
    """

    TEMPLATE_SUMDIR = """You are a world-class software engineer. You have been tasked to create a full code map of a repository by crawling it bottom to top. You have already summarized some of the files, now create a summary of the directory. Summarize the following directory up to seven sentences, containing the most important information in the directory. Write what the main functionality of the module is, what classes and methods are important, and what the main purpose of the module is. Do not violate the length constraint. Mention important classes and methods using `backticks`, but do not use ```codeblocks```. 
    If the directory is empty, respond with "This directory is empty.", else respond with "In this directory, ...".
    Do not mention your own name or the name of the directory in the response, only summarize the content of the directory.

    The directory contains the following directories and files:

{% for child in directorytosummarize.children %}
{% if child.__class__.__name__ == "SummarizedDirectory" %}
- Directory: {{child.relative_path}}: Summary: {{child.summary}}
{% else %}
- File: {{child.relative_path}}: Summary: {{child.summary}}
{% endif %}
{% endfor %}
"""

    def __init__(self, generator):
        self.prompt_builder_file = PromptBuilder(template=self.TEMPLATE_SUMFILE)
        self.prompt_builder_dir = PromptBuilder(template=self.TEMPLATE_SUMDIR)
        self.llm = generator

    @staticmethod
    def _filestructure2dict(path: str) -> dict:
        outp = subprocess.Popen(
            ["git", "ls-files", "--exclude-standard"],
            cwd=path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, _ = outp.communicate()
        filelist = stdout.decode("utf-8").split("\n")
        filedict = {}
        for f in filelist:
            p = filedict
            for d in str(f).split("/"):
                p = p.setdefault(d, {})
        filedict.pop("", None)
        return filedict

    def _dict2tree(
        self, filedict, base_path, summarize=False
    ) -> typing.Union[SummarizedDirectory, SummarizedFile]:
        def _rec(filedict, current_path, summarize):
            for children, children_values in filedict.items():
                relative_path = f"{current_path}/{children}".replace(base_path, "")
                if relative_path.startswith("/"):
                    relative_path = relative_path[1:]
                if len(children_values) == 0:
                    with open(f"{current_path}/{children}", "r") as f:
                        content = f.read()
                    res = SummarizedFile(relative_path=relative_path, content=content, summary="")
                    if summarize:
                        res.summary = self._summ_file(res)
                    yield res
                else:
                    res = SummarizedDirectory(
                        relative_path=relative_path,
                        children=list(
                            _rec(
                                filedict=children_values,
                                current_path=f"{current_path}/{children}",
                                summarize=summarize,
                            )
                        ),
                    )
                    if summarize:
                        res.summary = self._summ_dir(res)
                    yield res

        children = list(_rec(filedict, base_path, summarize))
        res = SummarizedDirectory(relative_path=".", children=children)
        if summarize:
            res.summary = self._summ_dir(res)
        return res

    def _summ_file(self, f: SummarizedFile) -> str:
        prompt = self.prompt_builder_file.run(filetosummarize=f)
        logger.debug(f"Summarizing file {f.relative_path}")
        response = self.llm.run(prompt["prompt"])
        return response["replies"][0]

    def _summ_dir(self, d: SummarizedDirectory) -> str:
        prompt = self.prompt_builder_dir.run(directorytosummarize=d)
        logger.debug(f"Summarizing directory {d.relative_path}")
        response = self.llm.run(prompt["prompt"])
        return response["replies"][0]

    def create_summary(self, path: str) -> SummarizedDirectory:
        filedict = self._filestructure2dict(path)
        summarized_dict = self._dict2tree(filedict, path, summarize=True)
        return summarized_dict


@haystack.component
class FileSelectionValidator:
    def __init__(self):
        self.all_paths = None
        # self.absolute_path = None

    @haystack.component.output_types(
        valid_replies=typing.List[str],
        invalid_replies=typing.Optional[typing.List[str]],
        error_message=typing.Optional[str],
    )
    def run(self, replies: typing.List[str]):
        assert self.all_paths is not None, "all_paths must be set before running the validator"
        # assert self.absolute_path is not None, "absolute_path must be set before running the validator"
        try:
            rep0 = replies[0]
            rep0 = rep0.strip(" `")
            rep0 = re.sub(r"^json\s*", "", rep0)
            rep0_list = ast.literal_eval(rep0)
            for file in rep0_list:
                if not isinstance(file, str):
                    raise ValueError("Each file must be a string")
                if file not in self.all_paths:
                    raise ValueError(
                        f"File {file} not found in the document store of {self.all_paths}"
                    )
            return {"valid_replies": [rep0_list]}
        except Exception as e:
            logger.debug(f"Error in output validation: {e}, model output was: {replies}")
            return {"invalid_replies": replies, "error_message": str(e)}


@haystack.component
class CodeMapRetriever:
    TEMPLATE_SELECT = """
You are a world-class software engineer. You have been tasked to collect files from a repository. There has been a very specific issue reported, and your tasks is to find the files that probably need be changed. The issue was 

{{issue}}

The following files are in the current repository: 

{% for child in code_map.children %}
{% if child.__class__.__name__ == "SummarizedDirectory" %}
- Directory: {{child.relative_path}}: Summary: {{child.summary}}
{% else %}
- File: {{child.relative_path}}: Summary: {{child.summary}}
{% endif %}
{% endfor %}

Please select the files that you think are most likely to be changed. You can select multiple files. Only pick the files that you think are most likely to be changed.
Time is of the essence, so you have to be quick while still very accurate.

Answer in list format containing the paths of the files you think are most likely to have the issue, sorted by importance. E.g.: in a directory with files `a.py`, `b.py`, `c.py`, you would answer `["c.py", "a.py"]` if you think `c.py` is most likely to have the issue, followed by `a.py`. Make sure to include the path of the file, not just the filename.

If you want to refrence a subdirectory, just select the directory. E.g. if you want to select the file in ./src/main.py, just select the directory ./src. You will be able to select the file in the next step. DO NOT USE THE FULL PATH, ONLY THE RELATIVE PATH FROM THE ROOT OF THE REPOSITORY.

REPLY ONLY WITH THE LIST, DO NOT ADD ANY EXTRA INFORMATION, NOT EVEN AN EXPLANATION. JUST RETURN THE LIST ["file1", "file2", ...]

Which of the files in {{all_paths}} do you think are most likely to have the issue?

{% if invalid_replies and error_message %}
  You already created the following output in a previous attempt: {{invalid_replies}}
  However, this doesn't comply with the format requirements from above and triggered this Python exception: {{error_message}}
  Correct the output and try again. Just return the corrected output without any extra explanations.
{% endif %}

"""

    def __init__(self, document_store: InMemoryDocumentStore, llm):
        self.document_store = document_store
        self.llm = copy.deepcopy(llm)
        self.code_map = None
        self.summarizer = Summarizer(llm)
        self.validator = FileSelectionValidator()
        self.pipeline = haystack.Pipeline(max_loops_allowed=3)
        self.prompt_builder = PromptBuilder(template=self.TEMPLATE_SELECT)
        self.pipeline.add_component(instance=self.prompt_builder, name="prompt_builder")
        self.pipeline.add_component(instance=self.validator, name="validator")
        self.pipeline.add_component(instance=self.llm, name="llm")
        self.pipeline.connect("prompt_builder", "llm")
        self.pipeline.connect("llm", "validator")
        self.pipeline.connect("validator.invalid_replies", "prompt_builder.invalid_replies")
        self.pipeline.connect("validator.error_message", "prompt_builder.error_message")
        self.absolute_path = None

    def select_recursive(
        self, node: typing.Union[SummarizedFile, SummarizedDirectory], query: str
    ) -> typing.List[str]:
        if isinstance(node, SummarizedFile):
            return [node.relative_path]
        else:
            logger.debug(
                f"select_recursive from directory {node.relative_path}, children: {[p.relative_path for p in node.children]}"
            )
            try:
                self.validator.all_paths = [c.relative_path for c in node.children]
                pipeline_res = self.pipeline.run(
                    data={
                        "prompt_builder": {
                            "code_map": node,
                            "issue": query,
                            "all_paths": [c.relative_path for c in node.children],
                        }
                    }
                )
                res = pipeline_res["validator"]["valid_replies"][0]
                logger.debug(f"Selected files: {res}, children of {node.relative_path}")
                for child in node.children:
                    if child.relative_path in res:
                        res += self.select_recursive(child, query)
                return res
            except Exception as e:
                logger.debug(f"Error in selecting files: {e}")
                return []

    def set_code_map(self, absolute_path: str):
        self.code_map = self.summarizer.create_summary(absolute_path)

    @haystack.component.output_types(documents=typing.List[haystack.Document])
    def run(self, query: str):
        assert self.code_map is not None, "Code map must be set before running the retriever"
        # assert self.absolute_path, "Absolute path must be set before running the retriever"
        selected_files = self.select_recursive(self.code_map, query)
        selected_files = list(set(selected_files))
        logger.debug(f"Selected files: {selected_files}")
        documents = []
        for doc in self.document_store.filter_documents():
            fpr = doc.meta["file_path_relative"].replace("\\", "/")
            if fpr in selected_files:
                documents.append(doc)
                selected_files.remove(fpr)
        logger.debug(f"Remaining files: {selected_files}, found {len(documents)} documents")
        return {"documents": documents}
