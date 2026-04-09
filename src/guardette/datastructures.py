from dataclasses import dataclass
from typing import Any

from starlette.datastructures import MutableHeaders


@dataclass
class ProxyRequest:
    url: str
    headers: MutableHeaders
    json_data: Any


@dataclass
class ProxyResponse:
    status_code: int
    headers: MutableHeaders
    json_data: Any
