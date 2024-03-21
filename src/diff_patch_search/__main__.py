import argparse
import os
from diff_patch_search.describe_repo import describe_repository
from diff_patch_search.generate_patch import generate_diff_patch


def main():
    parser = argparse.ArgumentParser(description='Describe repositories.')
    parser.add_argument('repo_paths', type=str, nargs='+', help='Path(s) to the repository directories')
    parser.add_argument('--affected-files', type=str, nargs='+', help='List of affected files to describe')
    parser.add_argument('--issue', type=str, help='Path to the issue description file')

    args = parser.parse_args()

    if os.path.exists("repo-description.txt"):
        os.remove("repo-description.txt")
    for repo_path in args.repo_paths:
        describe_repository(repo_path, args.affected_files)

    generate_diff_patch(args.issue)
    
if __name__ == '__main__':
    main()
