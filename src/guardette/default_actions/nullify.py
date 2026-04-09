from guardette.actions import Action, ActionContext, action_registry


@action_registry.register("nullify")
class RedactAction(Action):
    json_paths: list[str]

    async def response(self, ctx: ActionContext):
        for path in self.json_paths:
            ctx.update_json_path(ctx.response.json_data, path, None)
