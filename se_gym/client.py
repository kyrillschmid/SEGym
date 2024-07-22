import openai
from . import utils
from . import config
import instructor
import typing

__all__ = ["set_client"]


class _Client:
    _instance = None
    _initialized = False

    def __new__(cls, client: openai.Client = None):
        if cls._instance is None:
            cls._instance = super(_Client, cls).__new__(cls)
        return cls._instance

    def __init__(self, client: openai.Client = None):
        if not self._initialized:
            if client is None:
                raise ValueError("Client has to be initialized with an OpenAI client")
            _Client._instance = instructor.patch(client, mode=instructor.Mode.JSON)
            _Client._initialized = True

    @staticmethod
    @utils.cached(ignore=["response_model"])
    def completions_create(
        messages: typing.List[typing.Dict[str, str]],
        field_name: typing.Union[str, typing.List[str]] = "choices",
        **kwargs,
    ):
        assert _Client._instance is not None, "Client has to be initialized first"
        if "model" not in kwargs:
            kwargs["model"] = config.MODEL_NAME
        if "max_retries" not in kwargs:
            kwargs["max_retries"] = config.MAX_RETRIES
        if "timeout" not in kwargs:
            kwargs["timeout"] = config.TIMEOUT_SECONDS
        resp = _Client._instance.chat.completions.create(
            messages=messages,
            **kwargs,
        )
        if isinstance(field_name, list):
            return [getattr(resp, field) for field in field_name]
        else:
            return getattr(resp, field_name)


def set_client(client: openai.Client):
    _Client(client=client)


def LMU_get_openai_client():
    import openai
    import httpx
    import os
    import dotenv
    from . import utils

    dotenv.load_dotenv()
    USERNAME = os.getenv("API_USERNAME")
    PASSWORD = os.getenv("API_PASSWORD")
    assert USERNAME is not None, "API_USERNAME is not set in .env or file not found."
    assert PASSWORD is not None, "API_PASSWORD is not set in .env or file not found."
    openai.OpenAI.custom_auth = httpx.BasicAuth(USERNAME, PASSWORD)
    client = openai.OpenAI(base_url="https://ollama.mobile.ifi.lmu.de/v1/", api_key="none")
    utils.check_client(client)
    return client
