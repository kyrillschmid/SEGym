"""
This module contains possible fitness functions.
"""


def percent_successfull(test_results: dict) -> float:
    """
    Calculate the percentage of successful tests. This might incentivize the solver to avoid adding tests that are likely to fail.

    Args:
        test_results (dict): A dictionary with the test results.

    Returns:
        float: The percentage of successful tests.
    """
    num_failed = num_failed_tests(test_results)
    num_total = len(test_results)
    return (num_total - num_failed) / num_total


def num_failed_tests(test_results: dict) -> int:
    """
    Calculate the absolute number of failed or errored tests. This might incentivize the solver to avoid adding tests that are likely to fail.
    """
    return len(
        [
            k
            for k, v in test_results.items()
            if v["status"] == "failed" or v["status"] == "error"
        ]
    )


def execution_speed() -> float:
    """
    Calculate the end-to-end execution speed of the LLM generation. This might incentivize the solver to generate correct patches faster (no retries), but might also incentivize the solver to generate less tests.
    """


def number_retries() -> float:
    """
    Calculate the number of iterations a model needs to fix an issue. This might incentivize the solver to create larger patches, fixing multiple steps at once.
    """
