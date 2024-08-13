import openai
import haystack
import pydantic
import typing
import logging
from . import utils
from . import config

logger = logging.getLogger(__name__)


def patch_openai_auth():
    """
    Patch the OpenAI client to use the correct auth using the .env file.
    """
    import os
    import dotenv
    import requests

    dotenv.load_dotenv(".env")
    dotenv.load_dotenv("./se_gym/.env")
    username, password = os.getenv("API_USERNAME"), os.getenv("API_PASSWORD")
    assert (
        username is not None and password is not None
    ), "API_USERNAME and/or API_PASSWORD not set in .env"
    auth = requests.auth.HTTPBasicAuth(username, password)
    openai.Client.custom_auth = auth


@haystack.component()
class CustomGenerator:
    def __init__(
        self,
        model_config: typing.Dict[str, str],
        schema: typing.Optional[pydantic.BaseModel] = None,
        no_verify: bool = False,
    ):
        """
        Custom Haystack compliant generator for OpenAI API, usable for llama.cpp.

        :param model_config: Configuration for the OpenAI API, containing the base URL and API key.
        :param schema: Pydantic schema to validate the generated output.
        :param no_verify: If True, the output will not be validated against the schema. The schema will still be used to generate the JSON schema for the response.
        """
        if "api_key" not in model_config or model_config["api_key"] == "YOUR_KEY_HERE":
            model_config["api_key"] = "no-key"
        self.client = openai.OpenAI(
            base_url=model_config["base_url"],
            api_key=model_config["api_key"],
            max_retries=config.LLM_NUM_TIMEOUTS,
        )
        self.schema = schema
        self.no_verify = no_verify
        self.model_name = model_config.get("model_name", "unknown")

    @staticmethod
    def format_messages(messages: typing.Union[typing.List[typing.Dict[str, str]], str]):
        if isinstance(messages, str):
            return [{"role": "user", "content": messages}]
        elif isinstance(messages, dict):
            return [messages]
        elif isinstance(messages, list):
            if all(isinstance(m, dict) for m in messages):
                return messages
            elif all(isinstance(m, str) for m in messages):
                m = []
                for i, message in enumerate(messages[::-1]):
                    role = "user" if i % 2 == 0 else "assistant"
                    m.append({"role": role, "content": message})
                return m[::-1]
        else:
            raise ValueError(f"Unsupported type for messages: {type(messages)}")

    @haystack.component.output_types(
        replies=typing.List[str], meta=typing.List[typing.Dict[str, typing.Any]]
    )
    def run(self, prompt: str, schema: typing.Optional[pydantic.BaseModel] = None, **kwargs):
        messages = self.format_messages(prompt)
        schema = schema or self.schema

        if schema is not None:
            rf = dict(response_format={"type": "json_object", "schema": schema.model_json_schema()})
        else:
            rf = dict()

        # logger.debug(f"Calling {self.model_name} with messages: {messages} and kwargs: {kwargs} and rf: {rf}")

        completion = self.client.beta.chat.completions.parse(
            model=self.model_name,
            messages=messages,
            **rf,
            **kwargs,
            timeout=config.LLM_TIMEOUT,
        )

        choices = completion.choices[0]
        content = choices.message.content
        if schema is not None and not self.no_verify:
            try:
                schema.model_validate_json(content)
            except pydantic.ValidationError as e:
                try:
                    content = utils.remove_control_characters(content)
                    schema.model_validate_json(content)
                    logger.debug(
                        f"Removed control characters from response: {set(choices.message.content) - set(content)}"
                    )
                except pydantic.ValidationError:
                    logger.error(
                        f"Failed to validate response: {choices.message.content} to {schema}"
                    )
                    raise e

        return {"replies": [content], "meta": [completion.usage.to_dict()]}
