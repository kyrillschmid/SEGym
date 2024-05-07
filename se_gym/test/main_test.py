import os
import se_gym


def _download_einops():
    """
    Download einops repository to ./temp/einops
    """
    if not os.path.exists("./temp"):
        os.makedirs("./temp")
    with open("./temp/einops_issue.md", "w") as file:
        file.write("""
print("einops") does not work
""")
    if not os.path.exists("./temp/einops"):
        os.system(
            "git clone https://github.com/arogozhnikov/einops.git --depth 1  ./temp/einops && \
            cd ./temp/einops \
            git fetch --depth 1 origin fe9d81d577dec5a224d572a5bc7d44ab8bd914eb \
            "
        )


def _download_barcode():
    """
    Download barcode repository to ./temp/barcode
    """
    if not os.path.exists("./temp"):
        os.makedirs("./temp")
    with open("./temp/barcode_issue.md", "w") as file:
        file.write("""
print("barcode") does not work
""")
    if not os.path.exists("./temp/barcode"):
        os.system(
            "git clone https://github.com/WhyNotHugo/python-barcode.git --depth 1  ./temp/barcode"
        )
    with open("./temp/barcode/setup.cfg", "w") as file:
        file.write("") # empty file


def test_solve_barcode():
    _download_barcode()
    solver = se_gym.Solver()
    env = se_gym.Environment(base_dir="./temp/barcode")
    patch = solver.generate_patch(
        iteration=0,
        issue_description="./temp/barcode_issue.md",
        api="ollama_lmu",
        model="llama3:latest",
    )
    result = env.apply_patch_and_test(patch)


def test_solve_einops():
    _download_einops()
    solver = se_gym.Solver()
    env = se_gym.Environment(base_dir="./temp/einops")
    patch = solver.generate_patch(
        iteration=0,
        issue_description="./temp/einops_issue.md",
        api="ollama_lmu",
        model="llama3:latest",
    )
    with open("test.patch", "w") as file:
        file.write(patch)
    print(patch)
