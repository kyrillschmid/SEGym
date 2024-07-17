__all__ = ["get_generator"]


def get_generator(model: str = "phi3:3.8b", use_chat: bool = False):
    import requests
    import requests.auth
    import os
    import dotenv
    import warnings
    import haystack_integrations.components.generators.ollama.generator as gen
    import haystack_integrations.components.generators.ollama.chat.chat_generator as chat_gen

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
