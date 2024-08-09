import logging
import typing
from haystack.components.builders import PromptBuilder
import haystack

from . import observe
from . import config
from . import generator_singleton
from . import output_validator
from . import runner_host

logger = logging.getLogger(__name__)

__all__ = ["Sampler"]


class Sampler:
    PROMPT_TEMPLATE = """

{{trainable_prompt}}

Given the following codebase: 

{% for doc in documents %}
{{ doc.content }}
{% endfor %}

The issue description is as follows:
    
{{issue_description}}

{% if logs %}
The last time the code has been tested, the following logs were generated:
{% for log in logs %}
{{log}}
{% endfor %}
{% endif %}


Answer in the following json schema format:


"filename": {
    "description": "The filename of the file to be changed. Use the exact filename that was provided to you. Do not modify it. If you are modifying multiple files, only list one file here. You will be able to modify multiple files in the next step.",
    "type": "string",
},
"old_code": {
    "description": "The original code. Use the exact code that was provided to you. Do not modify it.",
    "type": "string",
},
"new_code": {
    "description": "The new code to replace the original code.",
    "type": "string",
},


EXAMPLE: If you want to replace the code in the file `./src/main.py` from `Hello, World!` to `Hello, new World!`, the JSON object should look like this:

{
    'filename': './src/main.py',
    'old_code': '\nif __name__ == "__main__":\n    print("Hello, World!")\n',
    'new_code': '\nif __name__ == "__main__":\n    print("Hello, new World!")\n'
}

{% if invalid_replies and error_message %}
  You already created the following output in a previous attempt: {{invalid_replies}}
  However, this doesn't comply with the format requirements from above and triggered this Python exception: {{error_message}}
  Correct the output and try again. Just return the corrected output without any extra explanations.
{% endif %}

"""

    def __init__(self, store: typing.Union[observe.Store, None] = None):
        if store is None:
            store = observe.Store(converter="ast", retriever="bm25")
        self.store = store

        self.prompt_builder = PromptBuilder(template=self.PROMPT_TEMPLATE)
        self.validator = output_validator.OutputValidator()
        self.pipeline = haystack.Pipeline(max_loops_allowed=config.MAX_RETRIES)

        self.pipeline.add_component(instance=self.prompt_builder, name="prompt_builder")
        self.pipeline.add_component(instance=self.store.retriever, name="retriever")
        self.pipeline.add_component(
            instance=generator_singleton.get_json_generator(), name="generator"
        )
        self.pipeline.add_component(instance=self.validator, name="validator")

        self.pipeline.connect("retriever.documents", "prompt_builder.documents")
        self.pipeline.connect("prompt_builder", "generator")
        self.pipeline.connect("generator", "validator")
        self.pipeline.connect("validator.invalid_replies", "prompt_builder.invalid_replies")
        self.pipeline.connect("validator.error_message", "prompt_builder.error_message")

    def update_current_state(self, state):
        self.code_base_root = state.path
        runner_host.apply_past_patches(state.repo, state.setup_commit, state.previous_patches)
        self.store.update(self.code_base_root)
        self.validator.update_state(state)

    # @utils.cached()
    def __call__(
        self,
        trainable_prompt: str,
        state,
    ) -> str:
        self.update_current_state(state)
        pipeline_res = self.pipeline.run(
            data={
                "prompt_builder": {
                    "trainable_prompt": trainable_prompt,
                    "issue_description": state.issue,
                    "logs": state.logs,
                },
                "retriever": {"query": state.issue},
            }
        )
        return pipeline_res["validator"]["valid_replies"][0]
