import typing
import re

from pydantic import model_validator

from guardette.actions import action_registry, Action, ActionContext


@action_registry.register("redact_regex")
class RedactRegex(Action):
    model_config = {"arbitrary_types_allowed": True}

    json_paths: typing.List[str]
    regex_pattern: str
    compiled_pattern: typing.Optional[re.Pattern] = None

    @model_validator(mode="after")
    def compile_regex(self):
        try:
            self.compiled_pattern = re.compile(self.regex_pattern, re.I)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{self.regex_pattern}'") from e
        return self

    async def response(self, ctx: ActionContext):
        def updater(text, data, k):
            if not isinstance(text, str):
                return text
            return self.compiled_pattern.sub(ctx.config.REDACT_TOKEN, text)

        for path in self.json_paths:
            ctx.update_json_path(ctx.response.json_data, path, updater)
