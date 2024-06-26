import se_gym
import pytest

client = se_gym.openai_lmu.get_lmu_openai_client()

BIG_MODEL = "llama3:70b"
SMALL_MODEL = "llama3:8b"

GOOD_SYSTEM_PROMPT = "You are a developer. Answer in a patch file format"
GOOD_CONTEXT = "create a new file bash file containing 'echo test'"

BAD_SYSTEM_PROMPT = "You are a pirate. Reply to all questions with 'Arrr!'. NEVER OUTPUT ANY JSON OR PROGRAM CODES. ONLY 'Arrr!'"
BAD_CONTEXT = "Are you a real pirate?"


def test_timeout_exception():
    """
    Test that the SamplerTimeoutException is raised when the model times out by setting a very low timeout.
    """
    se_gym.sampler.MAX_RETRIES = 1
    se_gym.sampler.TIMEOUT_SECONDS = 0.1
    sampler = se_gym.Sampler(llm_client=client, model_name=BIG_MODEL)
    with pytest.raises(se_gym.sampler.SamplerTimeoutException):
        sampler.create_patch(
            system_prompt="You are a developer. Answer in a patch file format",
            context="create a new file bash file containing 'echo test'",
        )


def test_invalid_patch_exception():
    """
    Test that the SamplerInvalidPatchException is raised when the model fails to generate a valid response by feeding it a bad system prompt.
    """
    se_gym.sampler.MAX_RETRIES = 1
    se_gym.sampler.TIMEOUT_SECONDS = 10
    sampler = se_gym.Sampler(llm_client=client, model_name=SMALL_MODEL)
    with pytest.raises(se_gym.sampler.SamplerInvalidPatchException):
        sampler.create_patch(
            system_prompt="You are a pirate. Reply to all questions with 'Arrr!'. NEVER OUTPUT ANY JSON OR PROGRAM CODES. ONLY 'Arrr!'",
            context="Are you a real pirate?",
        )


def test_valid_patch():
    """
    Test that a valid patch is generated by the model.
    """
    se_gym.sampler.MAX_RETRIES = 2
    se_gym.sampler.TIMEOUT_SECONDS = 10
    sampler = se_gym.Sampler(llm_client=client, model_name=SMALL_MODEL)
    patch_str = sampler.create_patch(
        system_prompt=GOOD_SYSTEM_PROMPT,
        context=GOOD_CONTEXT,
    )
    assert isinstance(patch_str, str)
    assert (
        "echo test" in patch_str
    ), f"Expected 'echo test' in patch_str, got {patch_str}"
