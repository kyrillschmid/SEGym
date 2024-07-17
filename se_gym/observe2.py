from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.retrievers import InMemoryEmbeddingRetriever, InMemoryBM25Retriever
from haystack.components.converters.txt import TextFileToDocument
import haystack
import typing
from pathlib import Path
import logging
import ast
from . import utils

logger = logging.getLogger("store")


@haystack.component
class PyFileToDocument:
    @haystack.component.output_types(documents=typing.List[haystack.Document])
    def run(
        self,
        sources: typing.List[typing.Union[str, Path]],
    ):
        documents = []
        for source in sources:
            with open(source, "r") as f:
                text = f.read()
            text = f"# {source}\n```python\n{text}\n```"
            doc = haystack.Document(content=text, meta={"name": source})
            documents.append(doc)
        return {"documents": documents}


class ASTExtractor(ast.NodeVisitor):
    """
    Helper class to extract docstrings from AST nodes.
    """

    def __init__(self):
        self.results = []

    def _get_fun(self, node):
        return {
            "type": "function",
            "name": node.name,
            "docstring": ast.get_docstring(node),
            "args": [ast.unparse(arg) for arg in node.args.args],
            "returns": ast.unparse(node.returns) if node.returns else None,
            "lineno": node.lineno - 1,
            "end_lineno": node.end_lineno,
        }

    def visit_ClassDef(self, node):
        class_info = {
            "type": "class",
            "name": node.name,
            "docstring": ast.get_docstring(node),
            "methods": [],
            "lineno": node.lineno - 1,
            "end_lineno": node.end_lineno,
        }
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                class_info["methods"].append(self._get_fun(item))
        self.results.append(class_info)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if isinstance(node.parent, ast.Module):
            self.results.append(self._get_fun(node))
        self.generic_visit(node)


@haystack.component
class PyASTToDocument:
    INDENT = "    "

    def __init__(self, kind: typing.Literal["skeleton", "full"] = "skeleton"):
        self.kind = kind

    @haystack.component.output_types(documents=typing.List[haystack.Document])
    def run(
        self,
        sources: typing.List[typing.Union[str, Path]],
    ):
        docs = []
        for source in sources:
            with open(source, "r") as f:
                filefull = f.read()
            if self.kind == "skeleton":
                docs += PyASTToDocument.ast2doc(source, filefull)
            elif self.kind == "full":
                docs += PyASTToDocument.split_code(source, filefull)
            else:
                raise NotImplementedError(f"Kind {self.kind} not implemented")
        return {"documents": docs}

    @staticmethod
    def add_parents(node):
        """Make sure each node has a reference to its parent."""
        for child in ast.iter_child_nodes(node):
            child.parent = node
            PyASTToDocument.add_parents(child)

    @staticmethod
    def ast2doc(filename, filefull):
        tree = ast.parse(filefull)
        PyASTToDocument.add_parents(tree)
        extractor = ASTExtractor()
        extractor.visit(tree)
        docs = []
        for item in extractor.results:
            docargs = dict(
                path=filename,
                start_line=item["lineno"],
                end_line=item["end_lineno"],
                full_text=filefull,
            )
            if item["type"] == "class":
                docs.append(
                    haystack.Document(content=PyASTToDocument.class2txt(item), meta=docargs)
                )
            elif item["type"] == "function":
                docs.append(
                    haystack.Document(content=PyASTToDocument.function2txt(item), meta=docargs)
                )
        return docs

    @staticmethod
    def class2txt(item):
        assert item["type"] == "class", f"Item is not a class but {item['type']}."
        doctxts = [f"class {item['name']}:"]
        if item["docstring"]:
            doctxts.append(f'{PyASTToDocument.INDENT}"""{item["docstring"]}"""')
        for method in item["methods"]:
            doctxts.append(PyASTToDocument.function2txt(method, indent=1))
        return "\n".join(doctxts)

    @staticmethod
    def function2txt(item, indent=0):
        assert item["type"] == "function", f"Item is not a function but {item['type']}."
        doctxts = []
        args = ", ".join(item["args"])
        if item["returns"]:
            doctxts.append(
                f"{PyASTToDocument.INDENT * indent}def {item['name']}({args}) -> {item['returns']}:"
            )
        else:
            doctxts.append(f"{PyASTToDocument.INDENT * indent}def {item['name']}({args}):")
        if item["docstring"]:
            doctxts.append(f'{PyASTToDocument.INDENT * (indent+1)}"""{item["docstring"]}"""')
        return "\n".join(doctxts)

    @staticmethod
    def split_code(filename, filefull) -> typing.List[haystack.Document]:
        def node2doc(code: str, node: ast.AST) -> haystack.Document:
            lines = code.splitlines()
            start_lineno = node.lineno - 1
            end_lineno = node.end_lineno
            text = "\n".join(lines[start_lineno:end_lineno])
            node_name = node.name if hasattr(node, "name") else ""
            node_name = f"{filename} - {node_name}"
            text = f"# {filename}\n" + f"```python\n{text}\n```"
            return haystack.Document(
                content=text,
                meta={"name": node_name, "start_lineno": start_lineno, "end_lineno": end_lineno},
            )

        tree = ast.parse(filefull)
        docs = []

        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                docs.append(node2doc(filefull, node))
            elif isinstance(node, ast.ClassDef):
                class_code = [node2doc(filefull, node)]
                for class_node in node.body:
                    if isinstance(class_node, ast.FunctionDef):
                        class_code.append(node2doc(filefull, class_node))
                docs.extend(class_code)

        return docs


class Store:
    def __init__(
        self,
        converter: typing.Literal["txt", "skeleton", "py", "ast"] = "txt",
        retriever: typing.Literal["oracle", "bm25", "embedding", "full"] = "bm25",
    ):
        self.document_store = InMemoryDocumentStore(
            embedding_similarity_function="dot_product", bm25_tokenization_regex=r"\b\w\w+\b"
        )
        # self.document_writer = DocumentWriter(
        #     document_store=self.document_store, policy="overwrite"
        # )

        self.path = None
        # self.query_pipeline = haystack.Pipeline()

        if converter == "txt":
            self.converter = TextFileToDocument()
            # self.query_pipeline.add_component(self.converter)
        elif converter == "skeleton":
            self.converter = PyASTToDocument(kind="skeleton")
            # self.query_pipeline.add_component(self.converter)
        elif converter == "ast":
            self.converter = PyASTToDocument(kind="full")
            # self.query_pipeline.add_component(self.converter)
        elif converter == "py":
            self.converter = PyFileToDocument()
            # self.query_pipeline.add_component(self.converter)
        else:
            raise NotImplementedError(f"Converter {converter} not implemented")

        if retriever == "bm25":
            self.retriever = InMemoryBM25Retriever(document_store=self.document_store, top_k=4)
            # self.query_pipeline.add_component(self.retriever)
            # self.document_embedder = None
        elif retriever == "embedding":
            self.retriever = InMemoryEmbeddingRetriever(document_store=self.document_store, top_k=4)
            # self.document_embedder = SentenceTransformersDocumentEmbedder()
            # self.document_embedder.warm_up()

            # self.query_pipeline.add_component("text_embedder", SentenceTransformersTextEmbedder())
            # self.query_pipeline.add_component(self.retriever)
            # self.query_pipeline.connect("text_embedder.embedding", "retriever.query_embedding")
        else:
            raise NotImplementedError(f"Retriever {retriever} not implemented")

    def update(self, path: Path):
        logger.info(f"Updating store with path {path}")
        if self.path is not None:
            # TODO: add a check to see which files have been added or removed and update only those
            # self.document_store.delete_documents()
            pass
        self.path = utils.str2path(path)
        files = list(self.path.rglob("*.py"))
        docs = self.converter.run(sources=files)["documents"]
        self.document_store.write_documents(docs)
