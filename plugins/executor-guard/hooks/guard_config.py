"""Read executor-guard's settings.

Settings live in `.claude/executor-guard.json`. The hooks use the nearest
one found by walking up from the session's working directory, then the
one in $CLAUDE_PROJECT_DIR. Every key is optional:

    {
      "allow": ["helm upgrade", "kubectl apply"],
      "protected_branches": ["main", "master"],
      "test_commands": ["./scripts/check.sh", "bazel test"],
      "ignore_paths": ["docs/*", "*.svg"]
    }

EXECUTOR_GUARD_ALLOW adds to "allow": a comma-separated list, for
example EXECUTOR_GUARD_ALLOW="helm upgrade,kubectl apply".
"""

import json
import os

CONFIG_NAME = os.path.join(".claude", "executor-guard.json")
ENV_ALLOW = "EXECUTOR_GUARD_ALLOW"
DEFAULT_PROTECTED = ("main", "master")


class Config(object):
    def __init__(self):
        self.path = None
        self.error = None
        self.allow = []
        self.protected_branches = list(DEFAULT_PROTECTED)
        self.test_commands = []
        self.ignore_paths = []

    def allows(self, rule):
        """True when an "allow" entry covers the rule id.

        An entry covers a rule when its words are the first words of the
        rule: "kubectl apply" covers "kubectl apply", "kubectl" covers
        every kubectl rule.
        """
        rule_words = rule.lower().split()
        for entry in self.allow:
            words = entry.lower().split()
            if words and rule_words[:len(words)] == words:
                return True
        return False


def _candidates(cwd):
    seen = set()
    d = os.path.abspath(cwd) if cwd else None
    while d:
        p = os.path.join(d, CONFIG_NAME)
        if p not in seen:
            seen.add(p)
            yield p
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if project:
        p = os.path.join(os.path.abspath(project), CONFIG_NAME)
        if p not in seen:
            yield p


def _string_list(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str) and v.strip()]
    return []


def load(cwd):
    cfg = Config()
    for path in _candidates(cwd):
        if not os.path.isfile(path):
            continue
        cfg.path = path
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                raise ValueError("the top level must be a JSON object")
        except (OSError, ValueError) as exc:
            cfg.error = "%s: %s" % (path, exc)
            break
        cfg.allow = _string_list(data.get("allow"))
        if "protected_branches" in data:
            cfg.protected_branches = _string_list(data.get("protected_branches"))
        cfg.test_commands = _string_list(data.get("test_commands"))
        cfg.ignore_paths = _string_list(data.get("ignore_paths"))
        break
    extra = os.environ.get(ENV_ALLOW, "")
    cfg.allow.extend(p.strip() for p in extra.split(",") if p.strip())
    return cfg
