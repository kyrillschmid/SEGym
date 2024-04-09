import argparse
import os

from diff_patch_search.environment import Environment
from diff_patch_search.solver import Solver


def main():
    parser = argparse.ArgumentParser(description='Describe repositories.')
    parser.add_argument('repo_paths', type=str, nargs='*', help='Path(s) to the repository directories', default=None)
    parser.add_argument('--affected-files', type=str, nargs='*', help='List of affected files to describe', default=None)
    parser.add_argument('--issue', type=str, help='Path to the issue description file', default=None)
    
    args = parser.parse_args()

    if not args.repo_paths:
        parser.error("the following arguments are required: repo_paths")
    if not args.issue:
        parser.error("the following arguments are required: issue")

    if os.path.exists("repo-description.txt"):
        os.remove("repo-description.txt")

    solver = Solver(args)
    env = Environment()

    api = 'openai' # 'openai' , 'ollama_lmu', 'ollama_local', 'groq'
    model = 'gpt-4-0125-preview' # gpt-4-0125-preview ,mistral,  mixtral-8x7b-32768
    patch = solver.generate_diff_patch(args.issue, api, model)
    result = env.apply_patch_and_test(patch)

    print(f"Evaluated model {model} with result:")
    print(f"Patch Applicable : {result[0]}, All Tests Passed : {result[1]}")
    print("-------------------------------")
    
    
if __name__ == '__main__':
    main()
