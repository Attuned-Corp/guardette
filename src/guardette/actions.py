import typing
from pydantic import BaseModel
from dataclasses import dataclass
from jsonpath_ng.ext import parse
from guardette.config import ConfigManager

from guardette.datastructures import ProxyRequest, ProxyResponse
from guardette.secrets import SecretsManager


_json_path_cache = {}


@dataclass
class ActionContext:
    config: ConfigManager
    secrets: SecretsManager
    request: ProxyRequest
    response: ProxyResponse

    def get_json_path_expr(self, path):
        expr = _json_path_cache.get(path)
        if expr is None:
            expr = _json_path_cache[path] = parse(path)
        return expr

    def update_json_path(self, data, path, updater):
        expr = self.get_json_path_expr(path)
        expr.update(data, updater)

    def filter_json_path(self, data, path, filter_fn):
        expr = self.get_json_path_expr(path)
        expr.filter(filter_fn, data)


class Action(BaseModel):
    ...

    async def request(self, ctx: ActionContext):
        ...

    async def response(self, ctx: ActionContext):
        ...


class ActionRegistry:
    def __init__(self):
        self.actions: typing.Dict[str, typing.Type[Action]] = {}

    def get_action_cls(self, kind: str):
        return self.actions[kind]

    def register(self, kind: str):
        def decorator(action: typing.Type[Action]):
            if kind in self.actions:
                raise KeyError(f"Action already exists: '{kind}'")

            self.actions[kind] = action
            return action

        return decorator


action_registry = ActionRegistry()
