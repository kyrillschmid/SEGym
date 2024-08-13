#!/usr/bin/env python3
import argparse
import ast
import os

parser = argparse.ArgumentParser()
parser.add_argument(
    "--model_name", help="Name of the model in the Ollama format (e.g. 'llama3.1:8b')"
)
parser.add_argument(
    "--ollama_path",
    help="Path to the Ollama cache directory",
    default="/usr/share/ollama/.ollama/models/",
)
args = parser.parse_args()
model_name = args.model_name
ollama_path = args.ollama_path

if ollama_path[-1] != "/":
    ollama_path += "/"

try:
    with open(
        f"{ollama_path}manifests/registry.ollama.ai/library/{model_name.split(':')[0]}/{model_name.split(':')[1]}"
    ) as f:
        manifest = ast.literal_eval(f.read())
    sha = [
        layers["digest"]
        for layers in manifest["layers"]
        if layers["mediaType"] == "application/vnd.ollama.image.model"
    ][0]
    print(f"Found sha256 digest: {sha}")

    gguf_path = f"{ollama_path}blobs/sha256-{sha[7:]}"
    os.stat(gguf_path)
    print(f"Found gguf at\n{gguf_path}")

except FileNotFoundError:
    print(f"Model {model_name} not found in {ollama_path}")
    exit(1)
except IndexError:
    print(f"Model {model_name} does not have a valid digest")
    exit(1)
