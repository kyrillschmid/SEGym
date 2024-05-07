import os
import se_gym


def _download_einops():
    """
    Download einops repository to ./temp/einops
    """
    if not os.path.exists("./temp"):
        os.makedirs("./temp")
    if not os.path.exists("./temp/einops"):
        os.system(
            "git clone https://github.com/arogozhnikov/einops.git --depth 1  ./temp/einops"
        )


def test_solver():
    solver = se_gym.solver.Solver()
