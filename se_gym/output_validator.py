import haystack
import typing
import re
import ast
import pydantic
import pathlib
import logging

from . import utils
from . import runner_host

logger = logging.getLogger("output_validator")


class ChangePatchOutput(pydantic.BaseModel):
    filename: str = pydantic.Field(
        description="The filename of the file to be changed. Use the exact filename that was provided to you. Do not modify it. If you are modifying multiple files, only list one file here. You will be able to modify multiple files in the next step."
    )
    old_code: str = pydantic.Field(
        description="The original code. Use the exact code that was provided to you. Do not modify it."
    )
    new_code: str = pydantic.Field(description="The new code to replace the original code.")


@haystack.component
class OutputValidator:
    def __init__(
        self,
    ):
        self.retry_counter = 0
        self.code_base_root = None
        self.state = None

    def update_state(self, state):
        self.state = state

    @haystack.component.output_types(
        valid_replies=typing.List[str],
        invalid_replies=typing.Optional[typing.List[str]],
        error_message=typing.Optional[str],
    )
    def run(self, replies: typing.List[str]):
        logger.debug(f"OutputValidator received {replies}")
        if self.state is None:
            logger.critical("State is not set")
            raise ValueError("State is not set")
        self.retry_counter += 1
        try:
            rep0 = replies[0]

            # Remove the markdown code block often added by the models
            rep0 = re.sub(r"^```json\s*", "", rep0)
            rep0 = re.sub(r"\s*```$", "", rep0)

            # Convert the json string to a dictionary, more robust than using json.loads, allowing for single quotes, trailing commas, etc.
            rep0_dict = ast.literal_eval(rep0)

            # Validate that all the keys are present and have the correct types
            ChangePatchOutput(**rep0_dict)

            # Attempt to construct a patch file
            patch_str = runner_host.generate_patch(
                repo=self.state.repo,
                environment_setup_commit=self.state.setup_commit,
                past_patches=self.state.previous_patches,
                filename=rep0_dict["filename"],
                old_code=rep0_dict["old_code"],
                new_code=rep0_dict["new_code"],
            )

            logger.debug(
                f"Output {replies} (iteration {self.retry_counter}) is cleaned to {rep0_dict} and patched to {patch_str}"
            )

            self.retry_counter = 0
            return {"valid_replies": [patch_str]}

        except Exception as e:
            logger.debug(
                f"Error in output validation (iteration {self.retry_counter}): {e}, model output was: {replies}"
            )
            return {"invalid_replies": replies, "error_message": str(e)}
