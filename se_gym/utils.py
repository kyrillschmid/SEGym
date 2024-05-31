from functools import wraps
import pickle
import logging
from inspect import signature

logger = logging.getLogger("utils")


def slugify(value, allow_unicode=False):
    """
    Taken from Django's https://github.com/django/django/blob/main/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    import unicodedata
    import re

    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


def cached(ignore=None):
    if ignore is None:
        ignore = []

    def decorator(func):
        def get_key(args, kwargs):
            sig = signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            cache_key = tuple(
                (k, v) for k, v in bound_args.arguments.items() if k not in ignore
            )
            return slugify(cache_key)

        cache_file = f"{func.__name__}.cache.pkl"
        try:
            with open(cache_file, "rb") as f:
                func.cache = pickle.load(f)
                logger.debug(
                    f"Loaded cache from {cache_file}, keys: {list(func.cache.keys())}"
                )
        except FileNotFoundError:
            logger.debug(f"Cache file {cache_file} not found. Creating new cache.")
            func.cache = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = get_key(args, kwargs)
            if key in func.cache:
                return func.cache[key]
            else:
                func.cache[key] = result = func(*args, **kwargs)
                with open(cache_file, "wb") as f:
                    pickle.dump(func.cache, f)
                return result

        return wrapper

    return decorator
