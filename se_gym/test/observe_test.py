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


def test_observer1():
    _download_einops()
    state = se_gym.api.State(path="./temp/einops", issue="einmix is not working")
    readers = [
        se_gym.observe.read.RawReader(root_dir="./temp/einops"),
        se_gym.observe.read.OracleReader(
            files=[
                "./temp/einops/einops/__init__.py",
                "./temp/einops/einops/layers/_einmix.py",
            ]
        ),
    ]

    selectors = [
        se_gym.observe.select.BM25Selector(),
        se_gym.observe.select.FullSelector(),
    ]

    compressors = [
        se_gym.observe.compress.NoCompression(),
    ]

    for r in readers:
        for s in selectors:
            for c in compressors:
                r.clear_cache()
                s.clear_cache()

                obs = se_gym.observe.Observer(reader=r, selector=s, compressor=c)
                result = obs(state)
                assert isinstance(result, str)
                assert len(result) > 0
