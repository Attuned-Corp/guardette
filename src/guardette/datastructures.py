import typing
from dataclasses import dataclass
from starlette.datastructures import MutableHeaders


@dataclass
class ProxyRequest:
    url: str
    headers: MutableHeaders
    json_data: typing.Any


@dataclass
class ProxyResponse:
    status_code: int
    headers: MutableHeaders
    json_data: typing.Any
