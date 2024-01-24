import typing

F = typing.TypeVar("F", bound=typing.Callable)


def copy_signature(_: F) -> typing.Callable[..., F]:
    return lambda f: f
