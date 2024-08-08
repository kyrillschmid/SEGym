__all__ = ["set_generator"]
import copy
from . import config
from . import utils
import warnings


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
    assert _Generator._initialized, "Generator has to be initialized"
    try:
        return copy.deepcopy(_Generator._instance)
    except Exception as e:
        warnings.warn(f"Failed to deepcopy generator, returning flat instance. {e}")
        return _Generator._instance


def get_json_generator():
    gen = get_generator()
    if not hasattr(gen, "_create_json_payload"):
        warnings.warn(
            "This generator does not support JSON generation or has not been patched to do so."
        )
        return gen
    _create = copy.deepcopy(gen._create_json_payload)
    gen._create_json_payload = lambda *args, **kwargs: {
        **_create(*args, **kwargs),
        "format": "json",
    }
    return gen


def LMU_get_ollama_generator(model=None, use_chat=False):
    import requests
    import requests.auth
    import os
    import dotenv
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


def _LMU_list_models(speedtest=False):
    import ollama
    import requests
    import dotenv
    import os

    dotenv.load_dotenv(".env")
    dotenv.load_dotenv("./se_gym/.env")
    client = ollama.Client(
        host="https://ollama.mobile.ifi.lmu.de/api/",
        auth=requests.auth.HTTPBasicAuth(os.getenv("API_USERNAME"), os.getenv("API_PASSWORD")),
    )
    models = client.list()
    models = sorted(models["models"], key=lambda x: x["size"])
    pop = ["modified_at", "model", "digest", "details", "parameter_size", "quantization_level"]
    for m in models:
        for p in pop:
            m.pop(p, None)

    if speedtest:

        @utils.timeout_after(10)
        def test(model):
            res = client.chat(
                model=model,
                messages=[
                    dict(
                        role="user",
                        content="What are the first 5 sentences of the declaration of independence?",
                    )
                ],
                options=dict(num_predict=100),
            )
            if isinstance(res, Exception):
                return -1
            else:
                return res["eval_count"] / res["eval_duration"] * 10**9

        def get_speed(model, n=3):
            best = -1
            for _ in range(n):
                try:
                    speed = test(model)
                    print(f"Speed of {model}: {speed} tokens/s")
                    if speed > best:
                        best = speed
                except Exception:
                    pass
            return best

        for model in models:
            model["speed"] = get_speed(model["name"], 3)

    return models
