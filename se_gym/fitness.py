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
