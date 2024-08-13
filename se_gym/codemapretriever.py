from haystack.components.builders import PromptBuilder
from haystack.document_stores.in_memory import InMemoryDocumentStore
import haystack
import copy
import typing
import logging
import ast
import re
import pydantic
from . import config
from . import generators
from . import utils

logger = logging.getLogger(__name__)

__all__ = ["CodeMapRetriever"]


class _DocumentDirectory(haystack.Document):
    pass


class _DocumentDirectoryRoot(_DocumentDirectory):
    pass


@haystack.component
class FileSelectionValidator:
    def __init__(self):
        self.all_paths = None

    @haystack.component.output_types(
        valid_replies=typing.List[str],
        invalid_replies=typing.Optional[typing.List[str]],
        error_message=typing.Optional[str],
    )
    def run(self, replies: typing.List[str]):
        assert self.all_paths is not None, "all_paths must be set before running the validator"
        try:
            rep0 = replies[0]
            rep0 = rep0.strip(" `")
            rep0 = re.sub(r"^json\s*", "", rep0)
            rep0_list = ast.literal_eval(rep0)
            if isinstance(rep0_list, dict):
                rep0_list = rep0_list["files"]
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
    template_select = """
You are a world-class software engineer. You have been tasked to collect files from a repository. There has been a very specific issue reported, and your tasks is to find the files that probably need be changed. The issue was 

{{issue}}

The following files are in the current repository: 

{% for child in node.meta.children %}
- {{child.meta.file_path_relative}}: Summary: {{child.meta.llm_summary}}
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

    template_sumfile = """
You are a world-class software engineer. You have been tasked to create a full code map of a repository by crawling it bottom to top. Summarize the following file in two or three sentences, containing the most important information in the file. Write only about the most relevant functions, methods and classes. Do not violate the length constraint. Mention important classes and methods using `backticks`, but do not use ```codeblocks```. 
If the file is empty, respond with "This file is empty.", else respond with "In this file, ...".
Do not mention your own name or the name of the file in the response, only summarize the content of the file.
Do not apologize for the length of the response or mention that the response is short.
If the file does not contain code but other content, still summarize the content of the file.


The filepath is {{relative_path}} 
The filecontent is:

```
{{file_content}}
```
"""

    template_sumdir = """
You are a world-class software engineer. You have been tasked to create a full code map of a repository by crawling it bottom to top. You have already summarized some of the files, now create a summary of the directory. Summarize the following directory up to seven sentences, containing the most important information in the directory. Write what the main functionality of the module is, what classes and methods are important, and what the main purpose of the module is. Do not violate the length constraint. Mention important classes and methods using `backticks`, but do not use ```codeblocks```. 
If the directory is empty, respond with "This directory is empty.", else respond with "In this directory, ...".
Do not mention your own name or the name of the directory in the response, only summarize the content of the directory.

The directory contains the following directories and files:

{% for child in directorytosummarize.meta.children %}
- {{child.meta.file_path_relative}}: Summary: {{child.meta.llm_summary}}
{% endfor %}
"""

    prompt_builder_file = PromptBuilder(template=template_sumfile)
    prompt_builder_dir = PromptBuilder(template=template_sumdir)

    def __init__(self, document_store: InMemoryDocumentStore):
        self.document_store = document_store
        self.llm = generators.CustomGenerator(
            model_config=config.RETRIEVER_MODEL_CONFIG, no_verify=True
        )
        self.validator = FileSelectionValidator()
        self.pipeline = haystack.Pipeline(max_loops_allowed=3)
        self.prompt_builder_select = PromptBuilder(template=self.template_select)
        self.pipeline.add_component(instance=self.prompt_builder_select, name="prompt_builder")
        self.pipeline.add_component(instance=self.validator, name="validator")
        self.pipeline.add_component(instance=self.llm, name="llm")
        self.pipeline.connect("prompt_builder", "llm")
        self.pipeline.connect("llm", "validator")
        self.pipeline.connect("validator.invalid_replies", "prompt_builder.invalid_replies")
        self.pipeline.connect("validator.error_message", "prompt_builder.error_message")
        self.absolute_path = None
        self._codemap_root = None

    @staticmethod
    def _summ_files(files: typing.List[haystack.Document], llm):
        """
        Add a summary to each file in the list of files.
        """
        logger.debug(f"Summarizing {len(files)} files")
        for f in files:
            f.meta["llm_summary"] = CodeMapRetriever._summ_file(f, llm)
        return files

    @staticmethod
    def _summ_file(d: haystack.Document, llm) -> str:
        """
        Create a summary for a file.
        """
        prompt = CodeMapRetriever.prompt_builder_file.run(
            relative_path=d.meta["file_path_relative"], file_content=d.content
        )
        logger.debug(f"Summarizing file {d.meta['file_path_relative']}")
        response = llm.run(prompt["prompt"])
        return response["replies"][0]

    @staticmethod
    def _summ_dir(d: _DocumentDirectory, llm) -> str:
        """
        Create a summary for a directory.
        """
        prompt = CodeMapRetriever.prompt_builder_dir.run(directorytosummarize=d)
        logger.debug(f"Summarizing directory {d.meta['file_path_relative']}")
        response = llm.run(prompt["prompt"])
        return response["replies"][0]

    @staticmethod
    def _summ_include_subdirectories(
        docs: typing.List[haystack.Document],
    ) -> typing.Dict[str, typing.List[typing.Union[str, haystack.Document]]]:
        """
        Construct a tree of directories and files from a list of documents.
        """
        intermediate_dirs = {}
        for doc in docs:
            path = doc.meta["file_path_relative"]
            path_without_filename = "/".join(path.split("/")[:-1])
            if path_without_filename not in intermediate_dirs:
                intermediate_dirs[path_without_filename] = []
            intermediate_dirs[path_without_filename].append(doc)
        updated_dirs = intermediate_dirs.copy()
        for dir_path in intermediate_dirs.keys():  # add directories that are not in the list, e.g. if a directory contains only other directories
            parts = dir_path.split("/")
            for i in range(1, len(parts)):
                parent_dir = "/".join(parts[:i])
                if parent_dir in updated_dirs:
                    updated_dirs[parent_dir].append(dir_path)
        return updated_dirs

    @staticmethod
    def _summ_create_dir_entry(
        all_intermediate_dirs: typing.Dict[str, typing.List[typing.Union[str, haystack.Document]]],
        llm,
        current: typing.Optional[str] = None,
        new_docs: typing.Optional[typing.List[_DocumentDirectory]] = None,
    ) -> typing.Tuple[_DocumentDirectoryRoot, typing.List[_DocumentDirectory]]:
        if current is None:
            current = list(all_intermediate_dirs.keys())[0]
        if new_docs is None:
            new_docs = []
        children = all_intermediate_dirs.get(current, [])
        clean_children = []
        for c in children:
            if isinstance(c, str):
                clean_children.append(
                    CodeMapRetriever._summ_create_dir_entry(
                        all_intermediate_dirs, llm=llm, current=c, new_docs=new_docs
                    )[0]
                )
            else:
                clean_children.append(c)

        new_dir = _DocumentDirectory(
            content=None, meta={"children": clean_children, "file_path_relative": current}
        )
        summary = CodeMapRetriever._summ_dir(new_dir, llm)
        new_dir.meta["llm_summary"] = summary
        new_docs.append(new_dir)
        return new_dir, new_docs

    def _summ_get_new_dir_docs(self, documents: typing.List[haystack.Document]):
        documents = CodeMapRetriever._summ_files(documents, llm=self.llm)
        all_intermediate_dirs = CodeMapRetriever._summ_include_subdirectories(documents)
        new_docs = self._summ_create_dir_entry(all_intermediate_dirs, llm=self.llm)[1]
        return documents + new_docs

    def get_summed_docs(self, documents: typing.List[haystack.Document], state=None):
        """
        Create a code map from a list of documents and return a new list of documents with summaries.
        """
        documents = copy.deepcopy(documents)
        if state is not None:
            new_docs = utils.cache(
                f"{state.repo}_{state.setup_commit}_{self.llm.model_name}_docs",
                self._summ_get_new_dir_docs,
                documents,
            )
        else:
            new_docs = self._summ_get_new_dir_docs(documents)
        self._codemap_root = new_docs[-1]
        return new_docs

    def _select_recursive(self, node: haystack.Document, query: str) -> typing.List[str]:
        if not isinstance(node, _DocumentDirectory):
            return [node.meta["file_path_relative"]]  # file has been selected
        else:
            try:
                self.validator.all_paths = [
                    c.meta["file_path_relative"] for c in node.meta["children"]
                ]

                all_files = tuple([typing.Literal[f] for f in self.validator.all_paths])  # type: ignore

                class SelectableFiles(pydantic.BaseModel):
                    files: typing.Set[typing.Union[all_files]]  # type: ignore

                pipeline_res = self.pipeline.run(
                    data={
                        "prompt_builder": {
                            "node": node,
                            "issue": query,
                            "all_paths": self.validator.all_paths,
                        },
                        "llm": {
                            "schema": SelectableFiles,
                        },
                    }
                )
                res = pipeline_res["validator"]["valid_replies"][0]
                logger.debug(
                    f"Dir `{node.meta['file_path_relative']}` possible selections: {self.validator.all_paths} selected: {res}"
                )
                for child in node.meta["children"]:
                    if child.meta["file_path_relative"] in res:
                        res += self._select_recursive(child, query)
                return res
            except Exception as e:
                logger.debug(f"Error in selecting files: {e}")
                return []

    @haystack.component.output_types(documents=typing.List[haystack.Document])
    def run(self, query: str):
        assert (
            self._codemap_root is not None
        ), "set_code_map has to be called before running. Have you called store.update()?"
        selected_files = self._select_recursive(self._codemap_root, query)
        selected_files = list(set(selected_files))
        logger.debug(f"Selected files: {selected_files}")
        documents = []
        for doc in self.document_store.filter_documents():
            fpr = doc.meta["file_path_relative"].replace("\\", "/")
            if fpr in selected_files:
                if not isinstance(doc, _DocumentDirectory):
                    documents.append(doc)
                selected_files.remove(fpr)
        logger.debug(f"Remaining files: {selected_files}, found {len(documents)} documents")
        return {"documents": documents}
