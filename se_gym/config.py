MAX_RETRIES = 3
RAG_TOP_N = 4
TIMEOUT_SECONDS = 60
DEFAULT_SAVE_PATH = "./temp"
DOCKER_TAG = "pytest-env"
GIT_DISCARD_CHANGES = "git reset --hard HEAD"
GIT_DIFF = "git diff"
MODEL_CONFIG = dict(
    base_url="https://api.openai.com/v1/", api_key="YOUR_KEY_HERE", model_name="gpt-4o-mini"
)
EVO_MODEL_CONFIG = dict(
    base_url="https://api.openai.com/v1/", api_key="YOUR_KEY_HERE", model_name="gpt-4o-mini"
)
RETRIEVER_MODEL_CONFIG = dict(
    base_url="https://api.openai.com/v1/", api_key="YOUR_KEY_HERE", model_name="gpt-4o-mini"
)
LLM_TIMEOUT = 60
LLM_NUM_TIMEOUTS = 1
CACHE_DIR = "./.cache"
FUZZY_MATCH_THRESHOLD = 80
