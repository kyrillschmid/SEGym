import os
import typing
import aider
import aider.main
import aider.coders
import aider.coders.base_coder


def monkey_patch():
    """
    litellm is a dependency of aider. It uses httpx and requests to make HTTP requests. It currently does not support authentication via HTTP Basic Auth.
    """
    import aider.litellm
    from aider.coders.base_coder import litellm as base_coder_litellm
    from aider.sendchat import litellm as sendchat_litellm
    import requests
    import httpx
    import dotenv

    dotenv.load_dotenv(".env")
    assert os.environ["API_USERNAME"]
    assert os.environ["API_PASSWORD"]
    requestsauth = (os.environ["API_USERNAME"], os.environ["API_PASSWORD"])
    httpxauth = httpx.BasicAuth(os.environ["API_USERNAME"], os.environ["API_PASSWORD"])

    def get_patched(original, auth):
        return lambda *args, **kwargs: original(*args, **kwargs, auth=auth)

    class MonkeyHttpx:
        def __getattr__(self, name):
            if name == "stream":
                return get_patched(httpx.stream, httpxauth)
            else:
                return getattr(httpx, name)

    class MonkeyRequests:
        def __getattr__(self, name):
            if name == "get":
                return get_patched(requests.get, requestsauth)
            elif name == "post":
                return get_patched(requests.post, requestsauth)
            else:
                return getattr(requests, name)

    aider.litellm.litellm.httpx = MonkeyHttpx()
    aider.litellm.litellm.requests = MonkeyRequests()
    aider.litellm.litellm.ollama.httpx = MonkeyHttpx()
    aider.litellm.litellm.ollama.requests = MonkeyRequests()
    base_coder_litellm.httpx = MonkeyHttpx()
    base_coder_litellm.requests = MonkeyRequests()
    sendchat_litellm.httpx = MonkeyHttpx()
    sendchat_litellm.requests = MonkeyRequests()


def get_coder(gitroot: str, files: typing.List[str]) -> aider.coders.base_coder.Coder:
    os.environ["OLLAMA_API_BASE"] = "https://ollama.mobile.ifi.lmu.de"
    coder = aider.main.main(argv=files, return_coder=True, force_git_root=gitroot)
    return coder


monkey_patch()

if __name__ == "__main__":
    gitroot = "../temp/barcode/"
    files = ["../temp/barcode/barcode/base.py"]
    coder = get_coder(gitroot=gitroot, files=files)
    gen = coder.send_new_user_message(
        "In `base.Barcode`, adjust the default background to be grey instead of white."
    )
    print(list(gen))  # trigger the generator
