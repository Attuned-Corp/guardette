import re

from guardette.actions import action_registry, Action, ActionContext
from pydantic import Field, model_validator


@action_registry.register("filter_regex")
class FilterRegex(Action):
    model_config = {"arbitrary_types_allowed": True}

    json_paths: list[str]
    regex_pattern: str
    delimiter: str = Field(default="")
    compiled_pattern: re.Pattern | None = None

    @model_validator(mode="after")
    def compile_regex(self):
        try:
            self.compiled_pattern = re.compile(self.regex_pattern, re.I)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{self.regex_pattern}'") from e
        return self

    async def response(self, ctx: ActionContext):
        def updater(text, data, k):
            matches = self.compiled_pattern.findall(text)
            return self.delimiter.join(matches)

        for path in self.json_paths:
            ctx.update_json_path(ctx.response.json_data, path, updater)
