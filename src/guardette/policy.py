import re
import yaml
import typing
from pydantic import BaseModel, model_validator
from guardette.actions import action_registry, Action


class Rule(BaseModel):
    route: str
    actions: typing.List[Action]

    @model_validator(mode="before")
    def create_actions(cls, values: typing.Dict[str, typing.Any]):
        action_values = values.get("actions") or []
        values["actions"] = [
            action_registry.get_action_cls(v.pop("kind")).model_validate(v, strict=True)
            for v in action_values
        ]
        return values


class Source(BaseModel):
    host: str
    auth: typing.Optional[str] = None
    rules: typing.List[Rule]

    @model_validator(mode="before")
    def validate_auth(cls, values: typing.Dict[str, typing.Any]):
        auth = values.get("auth")
        if auth and not re.match(r'^(\w+|\w+:\w+)$', auth):
            raise ValueError(f"Invalid `auth` format: {auth}")
        return values


class Policy(BaseModel):
    version: str
    sources: typing.List[Source]

    @model_validator(mode="before")
    def validate_unique_hosts(cls, values: typing.Dict[str, typing.Any]):
        hosts = [source['host'] for source in values.get("sources") or []]
        if len(hosts) != len(set(hosts)):
            duplicates = set([host for host in hosts if hosts.count(host) > 1])
            raise ValueError(f"Only one source per host is supported. "
                             f"Duplicated hosts: {', '.join(duplicates)}")
        return values


def load_policy(path: str) -> Policy:
    with open(path, "r") as f:
        data = yaml.safe_load(f)

    policy = Policy(**data)
    return policy
