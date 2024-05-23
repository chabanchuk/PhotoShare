from typing import Callable

RESPONSE_MODDERS = {}


def register_modder(endpoint: str):
    def factory(modder: Callable):
        global RESPONSE_MODDERS
        RESPONSE_MODDERS[endpoint] = modder

        def inner():
            pass

        return inner
    return factory
