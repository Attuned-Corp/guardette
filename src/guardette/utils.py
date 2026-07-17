from collections.abc import Callable


def copy_signature[F: Callable](_: F) -> Callable[..., F]:
    return lambda f: f
