import argparse
import os
from diff_patch_search.describe_repo import describe_repository
from diff_patch_search.generate_patch import generate_diff_patch
from diff_patch_search.run_docker import run_docker_env
from diff_patch_search.run_docker import build_image_if_not_exists


def main():
    parser = argparse.ArgumentParser(description='Describe repositories.')
    # Make 'repo_paths' optional and default to None
    parser.add_argument('repo_paths', type=str, nargs='*', help='Path(s) to the repository directories', default=None)
    parser.add_argument('--affected-files', type=str, nargs='*', help='List of affected files to describe', default=None)
    parser.add_argument('--issue', type=str, help='Path to the issue description file', default=None)
    parser.add_argument('--run-docker', action='store_true', help="Flag to only run docker env")
    parser.add_argument('--eval', action='store_true', help="Evaluate different models")

    args = parser.parse_args()

    if args.run_docker:
        run_docker_env()
        return

    # Ensure that mandatory fields are provided for non-docker operations
    if not args.repo_paths:
        parser.error("the following arguments are required: repo_paths")
    if not args.issue:
        parser.error("the following arguments are required: issue")

    if os.path.exists("repo-description.txt"):
        os.remove("repo-description.txt")

    for repo_path in args.repo_paths:
        describe_repository(repo_path, args.affected_files)

    #TODO: rebuild image if changes detected
    build_image_if_not_exists()

    api = 'openai' # 'openai' , 'ollama_lmu', 'ollama_local', 'groq'
    model = 'gpt-4-0125-preview' # gpt-4-0125-preview ,mistral,  mixtral-8x7b-32768

    if args.eval:
        patch = generate_diff_patch(args.issue, api, model)
        result = run_docker_env(patch)
        print(f"Evaluated model {model} with result:")
        print(f"Patch Applicable : {result[0]}, All Tests Passed : {result[1]}")
        print("-------------------------------")
        if not os.path.exists("patches"):
            os.makedirs("patches")
        with open(f'patches/{model}.patch', 'w') as file:
            file.write(patch)
            file.write('\n')
    
if __name__ == '__main__':
    main()
