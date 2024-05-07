import argparse
import os

from se_gym.environment import Environment
from se_gym.solver import Solver


def main():
    parser = argparse.ArgumentParser(description="Describe repositories.")
    parser.add_argument(
        "--api",
        type=str,
        help="Task type",
        default="which api to use",
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Task type",
        default="which model to use",
    )
    parser.add_argument(
        "--affected-files",
        type=str,
        nargs="*",
        help="List of affected files to describe",
        default=None,
    )
    parser.add_argument(
        "--issue", type=str, help="Path to the issue description file", default=None
    )
    args = parser.parse_args()

    if not args.issue:
        parser.error("the following arguments are required: issue")

    solver = Solver(affected_files=args.affected_files)
    env = Environment()

    if not args.api:
        api = "groq"  # 'openai' , 'ollama_lmu', 'ollama_local', 'groq'
    else:
        api = args.api
    if not args.model:
        model = "mixtral-8x7b-32768"  # gpt-4-0125-preview, mistral, mixtral-8x7b-32768
    else:
        model = args.model

    last_patch = None
    feedback = None

    for i in range(1):
        patch = solver.generate_patch(i, args.issue, api, model, last_patch, feedback)
        logs, result = env.apply_patch_and_test(patch)
        last_patch = patch
        feedback = logs
        if result[0] == 1 and result[1] == 1:
            break

    print(f"Evaluated model {model} with result:")
    print(f"Patch Applicable : {result[0]}, All Tests Passed : {result[1]}")
    print("-------------------------------")


if __name__ == "__main__":
    main()
