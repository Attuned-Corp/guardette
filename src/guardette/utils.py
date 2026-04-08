from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable)


def copy_signature(_: F) -> Callable[..., F]:
    return lambda f: f
