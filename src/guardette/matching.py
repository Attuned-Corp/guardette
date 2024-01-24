import typing
from fastapi import Request
from starlette.routing import compile_path
from guardette.policy import Policy, Rule, Source


class RuleMatcherResult(typing.TypedDict):
    path_params: typing.Dict[str, str | typing.Any]


class RuleMatcher:
    def __init__(self, rule: Rule):
        self.rule = rule
        self.method, path = rule.route.split(" ")
        self.path_regex, self.path_format, self.param_convertors = compile_path(path)

    def match(self, request: Request) -> RuleMatcherResult | None:
        if request.method != self.method:
            return None

        regex_match = self.path_regex.match(request.url.path)
        if not regex_match:
            return None

        matched_params = regex_match.groupdict()
        for key, value in matched_params.items():
            matched_params[key] = self.param_convertors[key].convert(value)
        return {"path_params": matched_params}


class SourceMatcherResult(typing.TypedDict):
    target: Source
    rule: Rule
    path_params: typing.Dict[str, str | typing.Any]


class SourceMatcher:
    def __init__(self, target: Source):
        self.target = target
        self.rule_matchers = [RuleMatcher(rule) for rule in self.target.rules]

    def match(self, request: Request) -> SourceMatcherResult | None:
        for r in self.rule_matchers:
            m = r.match(request)
            if m is not None:
                return {
                    "target": self.target,
                    "rule": r.rule,
                    "path_params": m["path_params"],
                }
        return None


class Matcher:
    def __init__(self, policy: Policy):
        self.policy = policy
        self.target_matchers = {
            target.host: SourceMatcher(target) for target in self.policy.sources
        }

    def match(self, request: Request, target_host: str):
        if target_host not in self.target_matchers:
            return None
        return self.target_matchers[target_host].match(request)
