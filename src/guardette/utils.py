from collections.abc import Callable


def copy_signature[F: Callable](_: F) -> Callable[[F], F]:
    def decorator(function: F) -> F:
        return function

    return decorator
