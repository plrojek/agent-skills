import json
import os
import unittest

import helpers
from helpers import STOP, TempDirCase, clean_env, run_hook

import require_tests


# Synthetic transcript lines, in the shape Claude Code writes them.

def prompt(text, **extra):
    line = {"type": "user", "isSidechain": False, "message": {"role": "user", "content": text}}
    line.update(extra)
    return line


def tool(name, tool_input, tool_id, sidechain=False):
    return {"type": "assistant", "isSidechain": sidechain, "message": {
        "role": "assistant",
        "content": [{"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}],
    }}


def result(tool_id, is_error=False):
    return {"type": "user", "isSidechain": False, "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tool_id, "content": "done", "is_error": is_error},
    ]}}


def say(text):
    return {"type": "assistant", "isSidechain": False,
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}


class StopCase(TempDirCase):
    def setUp(self):
        super(StopCase, self).setUp()
        self.project = os.path.join(self.tmp, "project")
        os.makedirs(self.project)
        self.n = 0

    def path(self, rel):
        return os.path.join(self.project, rel)

    def edit(self, rel, name="Edit"):
        self.n += 1
        tid = "toolu_%d" % self.n
        key = "notebook_path" if name == "NotebookEdit" else "file_path"
        return tid, tool(name, {key: self.path(rel) if not os.path.isabs(rel) else rel}, tid)

    def bash(self, command):
        self.n += 1
        tid = "toolu_%d" % self.n
        return tid, tool("Bash", {"command": command}, tid)

    def turn(self, *steps):
        """A prompt, then tool calls each followed by a successful result."""
        lines = [prompt("please do the task")]
        for step in steps:
            if isinstance(step, tuple):
                tid, line = step
                lines += [line, result(tid)]
            else:
                lines.append(step)
        return lines

    def stop(self, lines, active=False, env=None, raw_transcript=None, cwd=None):
        transcript = os.path.join(self.tmp, "session.jsonl")
        with open(transcript, "w") as fh:
            if raw_transcript is not None:
                fh.write(raw_transcript)
            else:
                for line in lines:
                    fh.write(json.dumps(line) + "\n")
        payload = {
            "session_id": "test",
            "hook_event_name": "Stop",
            "transcript_path": transcript,
            "cwd": cwd or self.project,
            "stop_hook_active": active,
            "last_assistant_message": "Done.",
        }
        code, out, err = run_hook(STOP, payload, env)
        self.assertEqual(code, 0, err)
        return json.loads(out) if out.strip() else None

    def assertBlocks(self, lines, **kw):
        decision = self.stop(lines, **kw)
        self.assertIsNotNone(decision, "expected the stop to be blocked")
        self.assertEqual(decision["decision"], "block")
        return decision["reason"]

    def assertLetsStop(self, lines, **kw):
        self.assertIsNone(self.stop(lines, **kw))


class BlockTest(StopCase):
    def test_edit_without_tests_blocks_once(self):
        lines = self.turn(self.edit("src/app.py"), say("Done, all fixed."))
        reason = self.assertBlocks(lines)
        self.assertIn("src/app.py", reason)
        self.assertIn("real output", reason)

    def test_loop_guard(self):
        lines = self.turn(self.edit("src/app.py"), say("Done."))
        self.assertLetsStop(lines, active=True)

    def test_each_edit_tool_counts(self):
        for name, rel in (("Write", "new.py"), ("MultiEdit", "a.go"), ("NotebookEdit", "nb.ipynb")):
            self.assertBlocks(self.turn(self.edit(rel, name)))

    def test_edit_after_the_last_test_run(self):
        lines = self.turn(self.edit("a.py"), self.bash("pytest -q"), self.edit("b.py"))
        self.assertIn("b.py", self.assertBlocks(lines))

    def test_meta_lines_and_tool_results_do_not_start_a_turn(self):
        lines = self.turn(self.edit("a.py"), prompt("<system-reminder>x</system-reminder>", isMeta=True))
        self.assertBlocks(lines)

    def test_config_test_commands_listed(self):
        self.write_config(self.project, {"test_commands": ["./scripts/check.sh"]})
        reason = self.assertBlocks(self.turn(self.edit("a.py")))
        self.assertIn("./scripts/check.sh", reason)


class LetStopTest(StopCase):
    def test_no_edits(self):
        self.assertLetsStop(self.turn(self.bash("ls"), say("Here's what I found.")))

    def test_tests_after_the_edit(self):
        for command in (
            "pytest -q", "python3 -m pytest tests/", "python3.12 -m unittest discover",
            "uv run pytest -x", "uv run --with pytest-cov pytest", "cd web && npm test",
            "npm --prefix web test", "npm run test:unit", "go build ./... && go vet ./... && go test ./...",
            "cargo test --workspace", "./gradlew :app:assembleDebug :app:testDebugUnitTest",
            "xcodebuild test -scheme App -destination 'platform=iOS Simulator,name=iPhone 16'",
            "make test", "FOO=1 make -C lib check", "bazel test //...",
        ):
            lines = self.turn(self.edit("src/app.py"), self.bash(command), say("Tests pass."))
            self.assertLetsStop(lines)

    def test_a_failing_test_run_still_counts(self):
        tid, line = self.bash("pytest")
        lines = self.turn(self.edit("a.py")) + [line, result(tid, is_error=True)]
        self.assertLetsStop(lines)

    def test_commands_that_are_not_tests(self):
        for command in ("npm install", "go run .", "git status", "echo pytest", "cat Makefile"):
            lines = self.turn(self.edit("a.py"), self.bash(command))
            self.assertBlocks(lines)

    def test_failed_edit_does_not_count(self):
        tid, line = self.edit("a.py")
        lines = [prompt("go"), line, result(tid, is_error=True), say("The edit failed.")]
        self.assertLetsStop(lines)

    def test_edits_in_an_earlier_turn_do_not_count(self):
        lines = self.turn(self.edit("a.py"), say("Done, not tested."))
        lines += [prompt("thanks, what's next?"), say("Next is the migration.")]
        self.assertLetsStop(lines)

    def test_docs_only(self):
        self.assertLetsStop(self.turn(self.edit("README.md"), self.edit("docs/notes.txt")))

    def test_files_outside_the_project(self):
        memory = os.path.join(os.path.expanduser("~"), ".claude", "projects", "x", "memory", "note.md")
        scratch = os.path.join(self.tmp, "scratchpad", "probe.py")
        lines = self.turn(self.edit(memory), self.edit(scratch))
        self.assertLetsStop(lines, cwd=self.project)

    def test_ignore_paths_from_config(self):
        self.write_config(self.project, {"ignore_paths": ["docs/*", "*.svg"]})
        self.assertLetsStop(self.turn(self.edit("docs/index.html"), self.edit("logo.svg")))
        self.assertBlocks(self.turn(self.edit("src/index.html")))

    def test_test_commands_from_config(self):
        lines = self.turn(self.edit("a.py"), self.bash("./scripts/check.sh --fast"))
        self.assertBlocks(lines)
        self.write_config(self.project, {"test_commands": ["./scripts/check.sh"]})
        self.assertLetsStop(lines)

    def test_sidechain_and_request_blob_lines_are_ignored(self):
        tid, _ = self.edit("a.py")
        blob = {"type": "api-request-blob", "message": {"content": [
            {"type": "tool_use", "id": tid, "name": "Edit", "input": {"file_path": self.path("a.py")}}]}}
        side = tool("Edit", {"file_path": self.path("b.py")}, "toolu_side", sidechain=True)
        self.assertLetsStop([prompt("go"), blob, side, say("Done.")])

    def test_unreadable_transcripts(self):
        self.assertLetsStop(None, raw_transcript="this is not json\n{\"type\": \"user\"\n")
        payload = {"hook_event_name": "Stop", "transcript_path": os.path.join(self.tmp, "missing.jsonl"),
                   "cwd": self.project, "stop_hook_active": False}
        code, out, _ = run_hook(STOP, payload)
        self.assertEqual((code, out), (0, ""))
        for raw in ("", "not json", "[]", '{"stop_hook_active": false}'):
            code, out, _ = run_hook(STOP, raw)
            self.assertEqual((code, out), (0, ""), raw)


class MatcherTest(unittest.TestCase):
    def setUp(self):
        self.patterns = require_tests._compile(require_tests.DEFAULT_TEST_COMMANDS)

    def test_matches(self):
        yes = ["pytest", "/repo/.venv/bin/pytest -k x", "python -m pytest", "npm t", "go test ./pkg/...",
               "mvnw verify", "./mvnw verify", "swift build -c release", "dotnet test App.sln"]
        no = ["npm ci", "go mod tidy", "python app.py", "make deploy", "git commit -m 'run pytest'",
              "xcodebuild -list", "cargo fmt"]
        for command in yes:
            self.assertTrue(require_tests.is_test_command(command, self.patterns), command)
        for command in no:
            self.assertFalse(require_tests.is_test_command(command, self.patterns), command)


if __name__ == "__main__":
    unittest.main()
