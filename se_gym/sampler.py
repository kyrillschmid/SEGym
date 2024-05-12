"""
This module allows to call a LLM to generate a patch file based on a given system prompt and context.

Several parts of this code are inspired by langchain.
https://github.com/langchain-ai/langchain/blob/70a79f45d78f4261418f9bf3a32a829bb63b94b2/libs/core/langchain_core/output_parsers/format_instructions.py
https://github.com/langchain-ai/langchain/blob/70a79f45d78f4261418f9bf3a32a829bb63b94b2/libs/core/langchain_core/output_parsers/json.py

"""

import instructor
import instructor.retry
import pydantic
import json
import openai
import logging
import tenacity
import time

from . import config
from . import runner

logger = logging.getLogger("caller")


def get_format_instructions(pydanticClass) -> str:
    """
    Turns a pydantic class into a JSON schema and returns the format instructions for it.
    """
    schema = {k: v for k, v in pydanticClass.model_json_schema().items()}  # copy
    reduced_schema = schema
    if "title" in reduced_schema:
        del reduced_schema["title"]
    if "type" in reduced_schema:
        del reduced_schema["type"]
    schema_str = json.dumps(reduced_schema)
    schema_prompt = (
        """
The output should be formatted as a JSON instance that conforms to the JSON schema below.\n\n
As an example, for the schema {"properties": {"foo": {"title": "Foo", "description": "a list of strings", "type": "array", "items": {"type": "string"}}}, "required": ["foo"]}
the object {"foo": ["bar", "baz"]} is a well-formatted instance of the schema. The object {"properties": {"foo": ["bar", "baz"]}} is not well-formatted.\n
Here is the output schema: \n\n
```\n"""
        + schema_str
        + """\n```
ONLY REPLY USING JSON FORMAT. DO NOT INCLUDE ANYTHING ELSE IN YOUR RESPONSE.

EXAMPLE:
Good patch files look like this: 
```
diff --git a/src/python_env/__main__.py b/src/python_env/__main__.py
index 2b39a9f..f1e21b3 100644
--- a/src/python_env/__main__.py
+++ b/src/python_env/__main__.py
@@ -2,8 +2,10 @@

 def main():
     print("hello world")
-    return 2
+    # return 2
+    return 3


 if __name__ == "__main__":
+    print("Calling main function...")
     main()
```
It modifies an existing file. The added lines start with a '+', the removed lines start with a '-'. In the header, starting with 'diff --git a/', the file paths are specified. In the section with @@ the line numbers are specified. \n
Embed good patch files in a JSON object with the key "patch_file".\n
"""
    )
    return schema_prompt


class SamplerInvalidPatchException(Exception):
    """
    Exception raised when the model fails to generate a valid response after MAX_RETRIES attempts
    """

    pass


class SamplerTimeoutException(Exception):
    """
    Exception raised when the API call times out after TIMEOUT_SECONDS seconds
    """

    pass


class Sampler:
    def __init__(self, llm_client: openai.Client, code_base_root: str = None):
        """
        Create a new Sampler for patch generation.

        Args:
            llm_client: OpenAI client object. It will be patched with instructor.
        """
        self.llm_client = instructor.patch(llm_client, mode=instructor.Mode.JSON)
        self.create_patch = self.__call__

        class Patch(pydantic.BaseModel):
            patch_file: str = pydantic.Field(
                description="Contents of a .patch file to change the codebase. Starts with 'diff --git a/'"
            )

            @pydantic.field_validator("patch_file")
            @classmethod
            def ensure_valid_patch(cls, patch_str: str) -> str:
                if not patch_str.startswith("diff --git a/"):
                    logger.debug(f"Invalid patch file {patch_str}")
                    raise ValueError("Patch file must start with 'diff --git a/'")
                if code_base_root is not None:
                    try:
                        runner.check_patch(code_base_root, patch_str)
                    except Exception as e:
                        logger.debug(f"Invalid patch file {patch_str} error {e}")
                        raise e
                else:
                    logger.debug(
                        "No code base root provided, skipping patch validation"
                    )
                return patch_str

        self.PATCH_CLASS = Patch

    def __call__(self, system_prompt: str, context: str) -> str:
        """
        Generate a patch file based on the given context.

        Args:
            system_prompt: System prompt to instruct the model. The patch file format instructions will be appended to it.
            context: Context for the model to generate a patch file. The exact format depends on the observation.

        Returns:
            str: Patch file contents

        Raises:
            instructor.retry.InstructorRetryException: If the model fails to generate a valid response after MAX_RETRIES attempts
            openai.APITimeoutError: If the API call times out after TIMEOUT_SECONDS seconds


        TODO:
        change `max_retries=MAX_RETRIES,` to
        ```
                max_retries=tenacity.Retrying(
                    stop=tenacity.stop_after_attempt(MAX_RETRIES),
                    after=lambda _: logger.debug("invalid respone", _),
                ),
        ```
        to log the invalid responses
        """
        system_prompt_instruct = system_prompt + get_format_instructions(
            self.PATCH_CLASS
        )
        messages = [
            {"role": "system", "content": system_prompt_instruct},
            {"role": "user", "content": context},
        ]
        start_time = time.time()
        logger.debug(
            f"Calling LLM with system prompt: {system_prompt_instruct} and context: {context}"
        )
        try:
            resp = self.llm_client.chat.completions.create(
                model=config.MODEL_NAME,
                messages=messages,
                response_model=self.PATCH_CLASS,
                max_retries=config.MAX_RETRIES,
                timeout=config.TIMEOUT_SECONDS,
            )
            logger.debug(f"API call took {time.time() - start_time} seconds")
            return resp.patch_file
        except instructor.retry.InstructorRetryException as e:
            logger.info(
                f"Failed to get a valid response after {config.MAX_RETRIES} attempts, last error:",
                e,
            )
            raise SamplerInvalidPatchException(e)
        except openai.APITimeoutError as e:
            logger.info(
                f"API call timed out after {config.TIMEOUT_SECONDS} seconds \
                        (took {time.time() - start_time}), last error:",
                e,
            )
            raise SamplerTimeoutException(e)
