from functools import wraps
import pickle
import logging
from inspect import signature
import os
import openai
import pandas as pd
import pathlib
import typing
import tempfile
import unicodedata
from . import config

logger = logging.getLogger(__name__)


def relpath(s: typing.Any, to: typing.Union[None, typing.Any] = None) -> str:
    """ "
    Get the current path relative to the temp directory.
    """
    s = str2path(s)
    if to is not None:
        to = str2path(to)
        modified_path = s.relative_to(to)
        return modified_path
    else:
        to = pathlib.Path(tempfile.gettempdir())
        modified_path = s.relative_to(to)
        modified_path = modified_path.relative_to(modified_path.parts[0])
        return modified_path


def str2path(s: typing.Any) -> str:
    """
    Attempt to convert a string into a pathlib.Path object.
    """
    if isinstance(s, pathlib.Path):
        return s
    if isinstance(s, str):
        # warnings.warn(f"path {s} is a string. Try to use pathlib.Path instead.", stacklevel=2)
        return pathlib.Path(s)
    if s is None:
        return
    raise ValueError(f"Invalid path {s}")


def log_to_parqet(log_filename: str, **kwargs):
    df_ = pd.DataFrame({k: [v] for k, v in kwargs.items()})
    if os.path.exists(log_filename):
        df = pd.read_parquet(log_filename)
        df = pd.concat([df, df_], ignore_index=True)
    else:
        df = df_
    df.to_parquet(log_filename)


def slugify(value):
    """
    Makes any object a url and filename friendly slug.
    Taken from Django's https://github.com/django/django/blob/main/django/utils/text.py
    """
    import unicodedata
    import re

    value = str(value)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
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
            cache_key = tuple((k, v) for k, v in bound_args.arguments.items() if k not in ignore)
            return slugify(cache_key)

        cache_file = f".cache.{func.__name__}.pkl"
        try:
            with open(cache_file, "rb") as f:
                func.cache = pickle.load(f)
                logger.debug(f"Loaded cache from {cache_file}, keys: {list(func.cache.keys())}")
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


def clear_store(store):
    store.delete_documents([d.id for d in store.filter_documents()])


def cache(identifier: str, func, *args, **kwargs):
    """
    If the there is a cache file with the same identifier, its content will be returned, otherwise the function will be called and the result will be saved in a cache file for future use.
    """
    if not config.CACHE_DIR:
        return func(*args, **kwargs)
    if not os.path.exists(config.CACHE_DIR):
        os.makedirs(config.CACHE_DIR)
    identifier = os.path.join(config.CACHE_DIR, f".{slugify(identifier)}.pkl")

    try:
        with open(identifier, "rb") as f:
            logger.debug(f"Loading cache from {identifier}")
            return pickle.load(f)
    except FileNotFoundError:
        logger.debug(f"Cache file {identifier} not found. Creating new cache")
        result = func(*args, **kwargs)
        with open(identifier, "wb") as f:
            pickle.dump(result, f)
        return result


def logging_setup():
    """
    Disable all logs except for the ones starting with "se_gym".
    """
    for log_name, log_obj in logging.Logger.manager.loggerDict.items():
        if log_name.startswith("se_gym"):
            log_obj.disabled = False
        else:
            log_obj.disabled = True
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)


def remove_control_characters(s):
    return "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")
