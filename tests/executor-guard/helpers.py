"""Shared helpers for the executor-guard tests."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

TESTS = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.path.join(os.path.dirname(os.path.dirname(TESTS)), "plugins", "executor-guard", "hooks")
if HOOKS not in sys.path:
    sys.path.insert(0, HOOKS)

GUARD = os.path.join(HOOKS, "guard_bash.py")
STOP = os.path.join(HOOKS, "require_tests.py")


def clean_env(**extra):
    """An environment with no executor-guard settings and no user git config."""
    env = dict(os.environ)
    for key in ("EXECUTOR_GUARD_ALLOW", "CLAUDE_PROJECT_DIR", "GIT_DIR", "GIT_WORK_TREE"):
        env.pop(key, None)
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["EXECUTOR_GUARD_STOP_RECHECK"] = "0"
    env.update(extra)
    return env


def run_hook(script, payload, env=None, cwd=None):
    """Feed `payload` (a dict, or a raw string) to a hook on stdin."""
    data = payload if isinstance(payload, str) else json.dumps(payload)
    proc = subprocess.run(
        [sys.executable, script], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, env=env or clean_env(), cwd=cwd, timeout=30,
    )
    return proc.returncode, proc.stdout, proc.stderr


def git(cwd, *args):
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
         "-c", "commit.gpgsign=false"] + list(args),
        cwd=cwd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=clean_env(),
    )


def make_repo(path, branch):
    os.makedirs(path)
    git(path, "init", "-q")
    git(path, "symbolic-ref", "HEAD", "refs/heads/" + branch)
    with open(os.path.join(path, "README.md"), "w") as fh:
        fh.write("test\n")
    git(path, "add", "README.md")
    git(path, "commit", "-q", "-m", "init")
    return path


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="executor-guard-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def write_config(self, directory, data):
        os.makedirs(os.path.join(directory, ".claude"), exist_ok=True)
        path = os.path.join(directory, ".claude", "executor-guard.json")
        with open(path, "w") as fh:
            fh.write(data if isinstance(data, str) else json.dumps(data))
        return path
