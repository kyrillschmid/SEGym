__all__ = ["set_generator"]
import copy


class _Generator:
    _instance = None
    _initialized = False

    def __new__(cls, generator=None):
        if cls._instance is None:
            cls._instance = super(_Generator, cls).__new__(cls)
        return cls._instance

    def __init__(self, generator=None):
        if not self._initialized:
            if generator is None:
                raise ValueError("Generator has to be initialized")
            _Generator._initialized = True
            _Generator._instance = generator


def set_generator(generator):
    _Generator(generator=generator)


def get_generator():
    return copy.deepcopy(_Generator._instance)
