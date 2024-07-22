__all__ = ["set_generator"]
import copy
from . import config


class _Generator:
    _instance = None
    _initialized = False

    def __new__(cls, generator=None):
        if cls._instance is None:
            cls._instance = super(_Generator, cls).__new__(cls)
        return cls._instance

    def __init__(self, generator=None):
        if not self._initialized:
            if generator is None:
                raise ValueError("Generator has to be initialized")
            _Generator._initialized = True
            _Generator._instance = generator


def set_generator(generator):
    _Generator(generator=generator)


def get_generator():
    return copy.deepcopy(_Generator._instance)


def LMU_get_ollama_generator(model=None, use_chat=False):
    import requests
    import requests.auth
    import os
    import dotenv
    import warnings
    import haystack_integrations.components.generators.ollama.generator as gen
    import haystack_integrations.components.generators.ollama.chat.chat_generator as chat_gen

    if model is None:
        model = config.MODEL_NAME

    dotenv.load_dotenv(".env")
    dotenv.load_dotenv("./se_gym/.env")
    USERNAME = os.getenv("API_USERNAME")
    PASSWORD = os.getenv("API_PASSWORD")
    assert USERNAME is not None, "API_USERNAME is not set in .env or file not found."
    assert PASSWORD is not None, "API_PASSWORD is not set in .env or file not found."

    class DummyRequest:
        def post(**kwargs):
            return requests.post(**kwargs, auth=requests.auth.HTTPBasicAuth(USERNAME, PASSWORD))

    gen.requests = DummyRequest
    chat_gen.requests = DummyRequest
    if use_chat:
        warnings.warn("Using chat generator. This is experimental and may not work as expected.")
        return chat_gen.OllamaChatGenerator(
            model=model, url="https://ollama.mobile.ifi.lmu.de/api/chat/"
        )
    else:
        return gen.OllamaGenerator(
            model=model, url="https://ollama.mobile.ifi.lmu.de/api/generate/"
        )


def LMU_get_openai_generator(model, api_key):
    from haystack.components.generators import OpenAIGenerator

    return OpenAIGenerator(model=model, api_key=api_key)