import openai
from . import utils
from . import config
import instructor
import typing


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
        resp = _Client._instance.chat.completions.create(
            messages=messages,
            model=config.MODEL_NAME,
            max_retries=config.MAX_RETRIES,
            timeout=config.TIMEOUT_SECONDS,
            **kwargs,
        )
        if isinstance(field_name, list):
            return [getattr(resp, field) for field in field_name]
        else:
            return getattr(resp, field_name)