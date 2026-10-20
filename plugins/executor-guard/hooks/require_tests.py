#!/usr/bin/env python3
"""Stop hook: if this turn changed files and no test or build command ran
after the last change, send Claude back once to run them or to say
plainly that it didn't.

It reads the session transcript (JSONL). Only the current turn counts:
tool calls after the last message that started it (a prompt, a queued
message, a task notification). Edits are Edit, Write, MultiEdit and
NotebookEdit calls that didn't fail; tests are Bash calls whose command
matches a test or build command (see DEFAULT_TEST_COMMANDS, extended
by "test_commands" in .claude/executor-guard.json).

It never traps a session: when stop_hook_active is set (Claude is
already continuing because of a stop hook), when the transcript is
missing or unreadable, or on any error, it lets Claude stop.
"""

import fnmatch
import json
import os
import re
import shlex
import sys
import tempfile
import time

sys.dont_write_bytecode = True  # keep the plugin directory clean
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import guard_config  # noqa: E402
import shell_words  # noqa: E402

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}

DEFAULT_TEST_COMMANDS = [
    # Python
    "pytest", "python -m pytest", "python -m unittest", "uv run pytest",
    "uv run python -m unittest", "poetry run pytest", "hatch test", "tox", "nox",
    # JavaScript and TypeScript
    "npm test", "npm t", "npm run test", "npm run build", "yarn test", "yarn build",
    "pnpm test", "pnpm build", "bun test", "bun run build", "npx jest", "npx vitest",
    "npx tsc", "jest", "vitest", "tsc", "npx playwright test", "deno test",
    # Go, Rust
    "go test", "go build", "go vet", "cargo test", "cargo build", "cargo check", "cargo nextest",
    # JVM
    "gradle", "gradlew", "mvn test", "mvn verify", "mvn package", "mvnw test", "mvnw verify",
    "mvnw package",
    # Apple
    "xcodebuild test", "xcodebuild build", "xcodebuild build-for-testing",
    "xcodebuild test-without-building", "swift test", "swift build",
    # Make, C and C++, Bazel
    "make test", "make check", "make build", "make all", "ctest", "cmake --build",
    "bazel test", "bazel build",
    # Others
    "dotnet test", "dotnet build", "bundle exec rspec", "rspec", "rake test", "rails test",
    "mix test", "phpunit", "composer test", "flutter test", "dart test",
]

DEFAULT_IGNORE = ["*.md", "*.mdx", "*.markdown", "*.txt", "*.rst", "*.adoc"]

_PYTHON = re.compile(r"^python[0-9.]*$")


def _norm(word):
    word = os.path.basename(word)
    return "python" if _PYTHON.match(word) else word


def _compile(patterns):
    out = []
    for p in patterns:
        try:
            words = shlex.split(p)
        except ValueError:
            continue
        if words:
            out.append([_norm(words[0])] + words[1:])
    return out


def _matches(argv, pattern):
    """The first word matches; the rest of the pattern appears in order.

    "npm test" matches `npm --prefix web test`; "npm run test" matches
    `npm run test:unit`. A loose match only ever means "tests ran", so
    it errs towards letting Claude stop.
    """
    if not argv or _norm(argv[0]) != pattern[0]:
        return False
    j = 1
    for want in pattern[1:]:
        while j < len(argv):
            got = argv[j] if not _PYTHON.match(argv[j]) else "python"
            j += 1
            if got == want or got.startswith(want + ":"):
                break
        else:
            return False
    return True


def is_test_command(command, patterns):
    for cmd in shell_words.commands(command):
        for pattern in patterns:
            if _matches(cmd.argv, pattern):
                return True
    return False


def _under(path, root):
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def _roots(cwd):
    roots = []
    for d in (cwd, os.environ.get("CLAUDE_PROJECT_DIR")):
        if d:
            roots.append(os.path.realpath(d))
    return roots


def _outside_dirs(scratchpad):
    """Places whose files aren't project work unless the project is there."""
    dirs = [os.path.join(os.path.expanduser("~"), ".claude"), tempfile.gettempdir(),
            "/tmp", "/var/folders"]
    if scratchpad:
        dirs.append(scratchpad)
    return [os.path.realpath(d) for d in dirs]


def _ignored(path, roots, extra, scratchpad):
    real = os.path.realpath(path)
    root = next((r for r in roots if _under(real, r)), None)
    if root is None and any(_under(real, d) for d in _outside_dirs(scratchpad)):
        return True
    rel = os.path.relpath(real, root) if root else real
    rel = rel.replace(os.sep, "/")
    name = os.path.basename(real)
    for pattern in DEFAULT_IGNORE + list(extra):
        if fnmatch.fnmatch(rel if "/" in pattern else name, pattern):
            return True
    return False


def _starts_turn(entry):
    """A user line that isn't a tool result starts a new turn."""
    if entry.get("isMeta"):
        return False
    msg = entry.get("message")
    if not isinstance(msg, dict):
        return False
    content = msg.get("content")
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                return False
        return True
    return False


def scan(transcript_path, patterns):
    """Walk the transcript. Returns a list of events for the current turn,
    each ("edit", path, tool_use_id) or ("test", command, tool_use_id),
    or None when the file can't be read."""
    events = []
    failed = set()
    try:
        fh = open(transcript_path, "r", encoding="utf-8", errors="replace")
    except OSError:
        return None
    with fh:
        for line in fh:
            if '"assistant"' not in line and '"user"' not in line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if not isinstance(entry, dict) or entry.get("isSidechain"):
                continue
            kind = entry.get("type")
            msg = entry.get("message")
            if not isinstance(msg, dict):
                continue
            content = msg.get("content")
            if kind == "user":
                if _starts_turn(entry):
                    events = []
                    failed = set()
                    continue
                if isinstance(content, list):
                    for block in content:
                        if (isinstance(block, dict) and block.get("type") == "tool_result"
                                and block.get("is_error")):
                            failed.add(block.get("tool_use_id"))
                continue
            if kind != "assistant" or not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name = block.get("name")
                tool_input = block.get("input") if isinstance(block.get("input"), dict) else {}
                if name in EDIT_TOOLS:
                    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
                    events.append(("edit", str(path), block.get("id")))
                elif name in SHELL_TOOLS:
                    command = tool_input.get("command")
                    if isinstance(command, str) and is_test_command(command, patterns):
                        events.append(("test", command, block.get("id")))
    return [e for e in events if not (e[0] == "edit" and e[2] in failed)]


def untested_edit(events, cwd, ignore, scratchpad):
    """The path of the last counted edit with no test after it, or None."""
    roots = _roots(cwd)
    last = None
    for kind, value, _ in events:
        if kind == "edit" and value and not _ignored(value, roots, ignore, scratchpad):
            last = value
        elif kind == "test":
            last = None
    return last


def _display(path, cwd):
    if cwd:
        base = cwd.rstrip("/\\") + os.sep
        if path.startswith(base):
            return path[len(base):]
    return path


def reason(path, cwd, cfg):
    examples = "pytest, python -m unittest, npm test, go test, cargo test, gradle, xcodebuild test, make test"
    if cfg.test_commands:
        examples += ", and from your config: " + ", ".join(cfg.test_commands)
    return (
        "executor-guard: files changed in this turn (last: %s) and no test or build command has "
        "run since. Before you finish, run the project's tests or build and include the real "
        "output in your reply. If you can't run them, say so plainly and tell the user what to "
        "run; don't describe the work as tested or verified. Commands that count include %s."
        % (_display(path, cwd), examples)
    )


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if not isinstance(data, dict) or data.get("stop_hook_active"):
        return 0
    transcript = data.get("transcript_path")
    if not isinstance(transcript, str) or not transcript:
        return 0
    transcript = os.path.expanduser(transcript)
    cwd = data.get("cwd") or os.getcwd()
    scratchpad = data.get("scratchpad_dir")
    cfg = guard_config.load(cwd)
    patterns = _compile(DEFAULT_TEST_COMMANDS + cfg.test_commands)

    path = None
    for attempt in range(2):
        events = scan(transcript, patterns)
        if events is None:
            return 0
        path = untested_edit(events, cwd, cfg.ignore_paths, scratchpad)
        if path is None:
            return 0
        if attempt == 0:
            # The transcript is written asynchronously; give a test run
            # that just finished a moment to land before blocking.
            time.sleep(float(os.environ.get("EXECUTOR_GUARD_STOP_RECHECK", "1.0")))
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason(path, cwd, cfg)}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:  # never keep a session from stopping because of a bug here
        sys.exit(0)
