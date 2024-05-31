import abc
import warnings
import dataclasses
import os
import glob
import typing


@dataclasses.dataclass
class Document:
    """
    A document. Path should be a unique identifier, like a file path.
    """

    path: str
    text: str

    def get_formatted(self):
        with_lines = ""
        for i, line in enumerate(self.text.split("\n")):
            with_lines += f"{i}: {line}\n"
        return f"# {self.path}\n{with_lines}"


class Reader(abc.ABC):
    """
    The reader is the first element of the retrieval chain.
    It reads some or all files in some way and returns the documents.
    """

    def __init__(self):
        self.cache = []

    def clear_cache(self):
        self.cache = []

    def get_documents(self) -> typing.List[Document]:
        if self.cache:
            return self.cache
        self.cache = self._populate()
        return self.cache

    @abc.abstractmethod
    def _populate(self): ...


class RawReader(Reader):
    """
    Reads everything in the code directory.
    """

    def __init__(self, root_dir, glob_pattern="**/*.py"):
        """
        Read all files in the directory.
        """
        super().__init__()
        self.root_dir = root_dir
        self.glob_pattern = glob_pattern
        self.path = os.path.join(root_dir, glob_pattern)

    def _populate(self):
        documents = []
        for f in glob.glob(self.path, recursive=True):
            with open(f, "r") as file:
                documents.append(Document(f.replace(self.root_dir, ""), file.read()))
        return documents


class OracleReader(Reader):
    """
    Read from manually selected files.
    This reader works with select.FullSelector, as it already contains the relevant files.
    """

    def __init__(self, root_dir: str, files: typing.List[str]):
        super().__init__()
        self.files = files
        self.root_dir = root_dir

    def _populate(self):
        files_existing = []
        for file in self.files:
            if not os.path.exists(file):
                warnings.warn(f"File {file} does not exist.")
            else:
                files_existing.append(file)
        self.files = files_existing
        documents = []
        for file in files_existing:
            with open(file, "r") as openfile:
                documents.append(
                    Document(file.replace(self.root_dir, ""), openfile.read())
                )
        return documents


class TreeReader(Reader):
    """
    Use TreeSitter to parse the code into an AST.
    Documents are containing the identifiers as paths and the method signatures and docs as text.
    """


class Summarizer(Reader):
    """
    Let an LLM create a code map, summarizing the contents of each file, then each directory.
    This reader is trainable.
    """


class CompressedReader(Reader):
    """
    Use an LLM to create an semantic compression of the code.
    """
