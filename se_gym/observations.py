import abc
import os
import warnings
import tree_sitter


class Observer(abc.ABC):
    """
    Abstract class for turning a state into an observation.
    """

    @abc.abstractmethod
    def __call__(self, state):
        """
        Turn a state into an observation.
        """
        pass


class ManualObserver(Observer):
    """
    Manually set the relevant files to observe.
    """

    def __init__(self, files, show_file_names=False):
        files_existing = []
        for file in files:
            if not os.path.exists(file):
                warnings.warn(f"File {file} does not exist.")
            else:
                files_existing.append(file)
        self.files = files_existing
        self.show_file_names = show_file_names

    def _print_files(self, files):
        indent_levels = dict()
        for file in files:
            indent_levels[file] = file.count(os.sep)
        max_indent = max(indent_levels.values())
        self.indent_levels = {file: max_indent - indent_levels[file] for file in files}
        file_strs = []
        for file in files:
            file_strs.append(
                self._print_file_contents(file, indent=self.indent_levels[file] * 4)
            )
        return "\n\n".join(file_strs)

    def _print_file_contents(self, file_path, indent=0):
        file_strs = []
        for line_number, line in enumerate(open(file_path), start=1):
            if self.show_file_names:
                fps = f"{file_path}:        "
            else:
                fps = ""
            file_strs.append(f"{fps}{' ' * indent}{line_number}: {line.rstrip()}")
        return "\n".join(file_strs)

    def __call__(self, relevant_files=None):
        if relevant_files is None:
            relevant_files = self.files
        return self._print_files(relevant_files)


class VectorStoreObserver(Observer):
    """
    Store all files in a FAISS vector store.
    """


class TreeSitterObeserver(Observer):
    """
    Use TreeSitter to parse the code and return the relevant files.
    """


class CodeMapObserver(Observer):
    """
    Let an LLM create a code map, summarizing the contents of each file, then each directory.
    Return the relevant files by first selecting the most relevant directories, then the most relevant files in those directories.

    Optimize LLM to create better map and better queries.
    """
