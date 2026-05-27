from contextlib import contextmanager

from detect_secrets.core.scan import _process_line_based_plugins
from detect_secrets.plugins.base import RegexBasedDetector
from detect_secrets.settings import default_settings

from guardette.actions import Action, ActionContext, action_registry


@contextmanager
def _full_match_regex_detectors():
    # Upstream RegexBasedDetector.analyze_string uses re.findall, which returns
    # only captured groups when present. Several built-in plugins (GitLab,
    # GitHub, ...) use capturing groups for alternation rather than secret
    # extraction, so the yielded secret_value is the prefix only. Swap in
    # finditer + group(0) so the whole token is what gets redacted.
    original = RegexBasedDetector.analyze_string

    def patched(self, string):
        for regex in self.denylist:
            for match in regex.finditer(string):
                yield match.group(0)

    RegexBasedDetector.analyze_string = patched
    try:
        yield
    finally:
        RegexBasedDetector.analyze_string = original


@action_registry.register("redact_secrets")
class RedactSecrets(Action):
    json_paths: list[str]

    async def response(self, ctx: ActionContext):
        token = ctx.config.REDACT_TOKEN

        def updater(value, parent, key):
            if not isinstance(value, str) or not value:
                return value
            # scan_line forces enable_eager_search=True (huge false-positive rate
            # on substrings), scan_file/scan_diff need the file on disk or in a
            # local git checkout. _process_line_based_plugins is the engine they
            # all wrap and accepts in-memory lines with a synthetic filename.
            lines = list(enumerate(value.splitlines(), start=1))
            redacted = value
            seen: set[str] = set()
            for secret in _process_line_based_plugins(lines, filename="scan.txt"):
                sv = secret.secret_value
                if sv and sv not in seen:
                    seen.add(sv)
                    redacted = redacted.replace(sv, token)
            return redacted

        with default_settings() as settings, _full_match_regex_detectors():
            # Always redact, even if upstream content contains an
            # `# pragma: allowlist secret` directive.
            settings.disable_filters("detect_secrets.filters.allowlist.is_line_allowlisted")
            for path in self.json_paths:
                ctx.update_json_path(ctx.response.json_data, path, updater)
