import se_gym
import os


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


def test_manual_observator():
    _download_einops()

    relevant_files = [
        "./temp/einops/einops/__init__.py",
        "./temp/einops/einops/layers/_einmix.py",
    ]

    obs = se_gym.ManualObserver(relevant_files, show_file_names=True)
    obs()
