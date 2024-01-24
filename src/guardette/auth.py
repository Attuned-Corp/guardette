import asyncio
import typing
from dataclasses import dataclass
from guardette.config import ConfigManager

from guardette.datastructures import ProxyRequest
from guardette.secrets import SecretsManager


@dataclass
class AuthContext:
    request: ProxyRequest
    secret_params: typing.Dict[str, str]
    config_params: typing.Dict[str, str | None]


AuthHandler = typing.Callable[[AuthContext], typing.Awaitable[None]]


class AuthHandlerRecord(typing.TypedDict):
    secret_keys: typing.Iterable[str]
    config_keys: typing.Iterable[str]
    handler: AuthHandler


class AuthHandlerRegistry:
    def __init__(self, handlers=None):
        self.handlers: typing.Dict[str, AuthHandlerRecord] = handlers or {}

    def register(
        self,
        kind,
        secret_keys: typing.Iterable[str],
        config_keys: typing.Iterable[str] | None = None,
    ):
        if config_keys is None:
            config_keys = []

        def decorator(handler: AuthHandler):
            if kind in self.handlers:
                raise KeyError(f"Auth handler already exists: '{kind}'")

            self.handlers[kind] = {
                "secret_keys": tuple(secret_keys),
                "config_keys": tuple(config_keys),
                "handler": handler,
            }
            return handler

        return decorator

    async def __call__(
        self,
        kinddef: str,
        /,
        request: ProxyRequest,
        secrets: SecretsManager,
        config: ConfigManager,
    ):
        kinddef_parts = kinddef.split(':')
        if len(kinddef_parts) == 1:
            kind = kinddef_parts[0]
            prefix = f"auth_{kind}"
        else:
            kind, subkind = kinddef_parts
            prefix = f"auth_{kind}_{subkind}"

        record = self.handlers[kind]
        secret_params: typing.Dict[str, str] = dict(
            zip(
                record["secret_keys"],
                await asyncio.gather(
                    *[
                        secrets.get(f"{prefix}_{k}".upper())
                        for k in record["secret_keys"]
                    ]
                ),
            )
        )

        config_params = dict(
            zip(
                record["config_keys"],
                [config.get(f"{prefix}_{k}".upper()) for k in record["config_keys"]],
            )
        )

        return await record["handler"](
            AuthContext(
                request=request,
                secret_params=secret_params,
                config_params=config_params,
            )
        )


auth_registry = AuthHandlerRegistry()
