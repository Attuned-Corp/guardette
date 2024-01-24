import typing
import re

from guardette.actions import action_registry, Action, ActionContext
from pydantic import Field


@action_registry.register("filter_regex")
class FilterRegex(Action):
    json_paths: typing.List[str]
    regex_pattern: str
    delimiter: str = Field(default="")

    async def response(self, ctx: ActionContext):
        def updater(text, data, k):
            matches = re.findall(self.regex_pattern, text, re.I)
            data.update({k: self.delimiter.join(matches)})

        for path in self.json_paths:
            ctx.update_json_path(ctx.response.json_data, path, updater)
