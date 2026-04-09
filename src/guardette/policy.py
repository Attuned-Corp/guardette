import re
from typing import Any

import yaml
from pydantic import BaseModel, model_validator

from guardette.actions import Action, action_registry


class Rule(BaseModel):
    route: str
    actions: list[Action]

    @model_validator(mode="before")
    def create_actions(cls, values: dict[str, Any]):
        action_values = values.get("actions") or []
        values["actions"] = [
            action_registry.get_action_cls(v.pop("kind")).model_validate(v, strict=True) for v in action_values
        ]
        return values


class Source(BaseModel):
    host: str
    auth: str | None = None
    rules: list[Rule]

    @model_validator(mode="before")
    def validate_auth(cls, values: dict[str, Any]):
        auth = values.get("auth")
        if auth and not re.match(r"^(\w+|\w+:\w+)$", auth):
            raise ValueError(f"Invalid `auth` format: {auth}")
        return values


class Policy(BaseModel):
    version: str
    sources: list[Source]

    @model_validator(mode="before")
    def validate_unique_hosts(cls, values: dict[str, Any]):
        hosts = [source["host"] for source in values.get("sources") or []]
        if len(hosts) != len(set(hosts)):
            duplicates = set([host for host in hosts if hosts.count(host) > 1])
            raise ValueError(f"Only one source per host is supported. Duplicated hosts: {', '.join(duplicates)}")
        return values

    @classmethod
    def from_file(cls, path: str) -> "Policy":
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)
