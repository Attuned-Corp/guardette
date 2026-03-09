import typing
import re

from guardette.actions import action_registry, Action, ActionContext


@action_registry.register("redact_regex")
class RedactRegex(Action):
    json_paths: typing.List[str]
    regex_pattern: str

    async def response(self, ctx: ActionContext):
        def updater(text, data, k):
            if not isinstance(text, str):
                return text
            return re.sub(self.regex_pattern, ctx.config.REDACT_TOKEN, text, flags=re.I)

        for path in self.json_paths:
            ctx.update_json_path(ctx.response.json_data, path, updater)
