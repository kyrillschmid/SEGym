import os
import json

from se_gym.call_api import call_model


TASK_TYPES = {
    #"list_files_to_be_changed": ["Select the files that need to be changed based on the issue description.", "listing files to be changed", "Affected files"], 
    #"detect_lines_to_be_changed_in_files": ["Detect the lines that need to be changed in the files based on the issue description.", "detecting lines to be changed in files", "Lines to be changed"],
    #"generate_code_snippets_for_changes": ["Generate the code snippets that need to be changed based on the issue description.", "generating code snippets for changes", "Code snippets for changes"],
    "create_patch_string": ["Create a patch string based on the issue description and the code base.", "creating patch strings for a given Python repository", "Patch string"]
}

JSON_SCHEMAS = {
#    "list_files_to_be_changed": {
#        "file": "string (full path to file)",
#    },
#    "detect_code_snippets_for_changes": {
#        "file": "string (full path to file)",
#        "details": "string (detailed info about code snippet)"
#    }, 
#    "detect_lines_to_be_changed_in_files": {
#        "file": "string (full path to file)",
#        "lines_to_be_changed_in_original_and_changed_file": "array of strings (@@ -1,2 +1,10 @@)",
#    },
#    "generate_code_snippets_for_changes": {
#        "file": "string (full path to file)",
#        "code_snippet": "string (code snippet)"
#    },
    "create_patch_string": {
        "patch_string": "string (diff --git a/...)"
    }
}

class Solver:
    def __init__(self, args):

        if os.path.exists("repo-description.txt"):
            os.remove("repo-description.txt")

        for repo_path in ['src', 'tests']:
            with open("repo-description.txt", 'a') as file:
                self.print_directory_contents(repo_path, args.affected_files, file)


    def get_system_prompt(self, task_type: str) -> str:
        # Fetch the specific instruction and JSON schema for the given analysis type
        specific_instruction = TASK_TYPES.get(task_type, "Perform the task as per the specified type.")[0]
        json_schema = JSON_SCHEMAS.get(task_type, {})

        # Format the JSON schema into a string representation
        json_schema_str = ', '.join([f"'{key}': {value}" for key, value in json_schema.items()])

        # Construct the system prompt with updated instruction
        return (f"You are an expert software engineer capable of creating patch strings to solve issues in a Python repository."
                f"Imagine that you have an executation environment with a Python interpreter from which you will receive feedback from your last patch string suggestion."
                f"Please respond directly in the following JSON format: "
                f"The JSON schema should include: {{{json_schema_str}}}. Provide nothing but the JSON output.")
    
    def print_directory_contents(self, path, affected_files, file):
        for root, dirs, files in os.walk(path):
            level = root.replace(path, '').count(os.sep)
            indent = ' ' * 4 * level
            file.write(f'{indent}{os.path.basename(root)}/\n')
            subindent = ' ' * 4 * (level + 1)
            for f in files:
                file.write(f'{subindent}{f}\n')
                if affected_files and f in affected_files:
                    self.print_file_contents(os.path.join(root, f), file, indent=subindent + ' ' * 4)

    def print_file_contents(self, file_path, file, indent=''):
        with open(file_path, 'r') as read_file:
            for line_number, line in enumerate(read_file, start=1):
                file.write(f'{indent}{line_number}: {line.rstrip()}\n')


    def generate_patch(self, iteration, issue_description, api, model, last_patch=None, feedback=None):
        
        with open("repo-description.txt", 'r') as file:
            repo_description = file.read()

        with open(issue_description, 'r') as file:
            issue = file.read()

        user_prompt = f"""Create a patch string based on the following issue description and the code base.\n"""
        user_prompt += f"""Code Base:\n{repo_description}\n"""
        user_prompt += f"""Issue:\n{issue}\n"""
        if last_patch is not None and feedback is not None:
            user_prompt += f"""Patch String from last suggestion:\n{last_patch}\n"""
            user_prompt += f"""Feedback from execution environment:\n{feedback}"""

        for i, task_type in enumerate(TASK_TYPES.keys()):

            system_prompt = self.get_system_prompt(task_type)

            if not os.path.exists(f'{model}'):
                os.mkdir(f'{model}')

            with open(f'{model}/prompt-{iteration}.md', 'w') as file:
                file.write("System Prompt:\n")
                file.write("----------------\n")
                file.write(system_prompt)
                file.write("\n\n")
                file.write("User Prompt:\n")
                file.write("--------------\n")
                file.write(user_prompt)

            """ with open(f'{model}/prompt-{i}.md', 'w') as file:
                file.write("System Prompt:\n")
                file.write("----------------\n")
                file.write(system_prompt)
                file.write("\n\n")
                file.write("User Prompt:\n")
                file.write("--------------\n")
                file.write(user_prompt) """
            
            json_data = call_model(system_prompt, user_prompt, api, model)
            
            user_prompt += f"""{TASK_TYPES[task_type][2]}: {json_data}\n"""

            # Create a new file
            with open(f'{model}/{task_type}.md', 'w') as file:
                file.write(json_data)

            if task_type == "create_patch_string":
                # write the patch to a file
                with open(f'{model}/{task_type}.patch', 'w') as file:
                    patch_dict = json.loads(json_data)
                    patch_string = patch_dict['patch_string']
                    file.write(patch_string)
                    file.write('\n')

        return patch_string