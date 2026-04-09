from guardette.actions import Action, ActionContext, action_registry


@action_registry.register("remove")
class RemoveAction(Action):
    json_paths: list[str]

    async def response(self, ctx: ActionContext):
        for path in self.json_paths:
            ctx.filter_json_path(ctx.response.json_data, path, lambda d: True)
