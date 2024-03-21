import os

def describe_repository(repo_path, affected_files):
    # check if file exists and recreate it
    with open("repo-description.txt", 'a') as file:
        print_directory_contents(repo_path, affected_files, file)

def print_directory_contents(path, affected_files, file):
    for root, dirs, files in os.walk(path):
        level = root.replace(path, '').count(os.sep)
        indent = ' ' * 4 * level
        file.write(f'{indent}{os.path.basename(root)}/\n')
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            file.write(f'{subindent}{f}\n')
            if affected_files and f in affected_files:
                print_file_contents(os.path.join(root, f), file, indent=subindent + ' ' * 4)

def print_file_contents(file_path, file, indent=''):
    with open(file_path, 'r') as read_file:
        for line_number, line in enumerate(read_file, start=1):
            file.write(f'{indent}{line_number}: {line.rstrip()}\n')