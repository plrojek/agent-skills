#!/usr/bin/env python3
"""PreToolUse hook for Bash: block the commands an executing session
shouldn't run on its own.

- git commit, git merge and git push while the current branch is
  protected (main and master unless configured)
- force pushes to a protected branch, and deleting one on the remote
- git stash in any form that changes the stash (all worktrees of a
  repository share one stash stack)
- deploys and cluster changes: helm upgrade/install/uninstall/rollback,
  kubectl apply/delete/rollout restart/scale/edit/patch,
  terraform (and tofu) apply/destroy

A blocked command exits 2 with the reason on stderr; Claude sees the
reason as the tool's error. Anything this script can't parse, and any
error inside it, lets the command through.
"""

import fnmatch
import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True  # keep the plugin directory clean
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import guard_config  # noqa: E402
import shell_words  # noqa: E402

_UNKNOWN = object()


class Block(object):
    def __init__(self, rule, what, reason):
        self.rule = rule  # the id an "allow" entry names
        self.what = what  # what was blocked, for the message
        self.reason = reason


# ---------------------------------------------------------------- git

_GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace",
                   "--super-prefix", "--config-env", "--list-cmds"}


def _parse_git(argv):
    """Split `git [global options] <subcommand> [args]`.

    Returns (repo_opts, subcommand, args) or None. repo_opts holds the
    options that change which repository git works on, so the branch
    lookup can use the same ones.
    """
    repo_opts = []
    i = 1
    while i < len(argv):
        a = argv[i]
        if a in _GIT_VALUE_OPTS:
            if i + 1 >= len(argv):
                return None
            if a in ("-C", "--git-dir", "--work-tree"):
                repo_opts += [a, argv[i + 1]]
            i += 2
            continue
        if a.startswith("--git-dir=") or a.startswith("--work-tree="):
            repo_opts.append(a)
            i += 1
            continue
        if a.startswith("-"):
            i += 1
            continue
        return repo_opts, a, argv[i + 1:]
    return None


def _branch_from_git(cwd, repo_opts, env):
    if cwd is None or not os.path.isdir(cwd):
        return None
    run_env = dict(os.environ)
    for key in ("GIT_DIR", "GIT_WORK_TREE"):
        if key in env:
            run_env[key] = env[key]
    try:
        out = subprocess.run(
            ["git"] + repo_opts + ["symbolic-ref", "--short", "-q", "HEAD"],
            cwd=cwd, env=run_env, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, universal_newlines=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None  # detached HEAD, not a repository, or no git
    return out.stdout.strip() or None


class _Branches(object):
    """Current branch per repository, following switches made earlier in
    the same command line (`git switch -c fix && git commit` is fine)."""

    def __init__(self):
        self.known = {}

    def key(self, cmd, repo_opts):
        return (cmd.cwd, tuple(repo_opts), cmd.env.get("GIT_DIR"), cmd.env.get("GIT_WORK_TREE"))

    def get(self, cmd, repo_opts):
        k = self.key(cmd, repo_opts)
        if k not in self.known:
            self.known[k] = _branch_from_git(cmd.cwd, repo_opts, cmd.env)
        value = self.known[k]
        return None if value is _UNKNOWN else value

    def note_switch(self, cmd, repo_opts, sub, args, protected):
        """Update the branch after git switch / git checkout."""
        k = self.key(cmd, repo_opts)
        if any(a in ("-h", "--help") for a in args):
            return
        if sub == "switch":
            new = _UNKNOWN
            i = 0
            while i < len(args):
                a = args[i]
                if a in ("-c", "-C", "--create", "--force-create", "--orphan") and i + 1 < len(args):
                    new = args[i + 1]
                    break
                if a in ("-d", "--detach"):
                    new = None
                    break
                if not a.startswith("-"):
                    new = _UNKNOWN if a == "-" else a
                    break
                i += 1
            self.known[k] = new
        elif sub == "checkout":
            if "--" in args:
                return  # git checkout -- <paths>: no branch change
            new = _UNKNOWN
            i = 0
            while i < len(args):
                a = args[i]
                if a in ("-b", "-B", "--orphan") and i + 1 < len(args):
                    new = args[i + 1]
                    break
                if a == "--detach":
                    new = None
                    break
                if not a.startswith("-"):
                    if cmd.cwd and os.path.exists(os.path.join(cmd.cwd, a)):
                        return  # a path, not a branch
                    # A branch or a commit; only trust protected names.
                    new = a if a in protected else _UNKNOWN
                    break
                i += 1
            self.known[k] = new


def _is_protected(branch, protected):
    if not branch:
        return False
    if branch.startswith("refs/heads/"):
        branch = branch[len("refs/heads/"):]
    return any(fnmatch.fnmatchcase(branch, p) or fnmatch.fnmatchcase(p, branch) for p in protected)


def _push_targets(args):
    """Parse git push arguments.

    Returns None for a dry run, otherwise a dict with force, mirror,
    all_branches, delete and refspecs (the arguments after the remote).
    """
    info = {"force": False, "mirror": False, "all_branches": False, "delete": False, "refspecs": []}
    positionals = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            positionals.extend(args[i + 1:])
            break
        if a.startswith("--"):
            name = a.split("=", 1)[0]
            if name in ("--force", "--force-with-lease"):
                info["force"] = True
            elif name == "--mirror":
                info["mirror"] = True
            elif name in ("--all", "--branches"):
                info["all_branches"] = True
            elif name == "--delete":
                info["delete"] = True
            elif name == "--dry-run":
                return None
            elif name in ("--help",):
                return None
            elif "=" not in a and name in ("--repo", "--receive-pack", "--exec", "--push-option"):
                i += 1
        elif a.startswith("-") and len(a) > 1:
            flags = a[1:]
            for k, ch in enumerate(flags):
                if ch == "f":
                    info["force"] = True
                elif ch == "d":
                    info["delete"] = True
                elif ch == "n":
                    return None
                elif ch == "h":
                    return None
                elif ch == "o":
                    if k == len(flags) - 1:
                        i += 1
                    break
        else:
            positionals.append(a)
        i += 1
    info["refspecs"] = positionals[1:]
    return info


def _check_push(args, branch, protected):
    info = _push_targets(args)
    if info is None:
        return None
    on_protected = _is_protected(branch, protected)

    rewrites = []  # (destination, how): force, delete or push
    if info["mirror"]:
        rewrites.append(("every branch", "force"))
    if info["all_branches"] and info["force"]:
        rewrites.append(("every branch", "force"))
    refspecs = info["refspecs"]
    if not refspecs and not info["all_branches"] and not info["mirror"]:
        if info["force"] and on_protected:
            rewrites.append((branch, "force"))
    for spec in refspecs:
        plus = spec.startswith("+")
        s = spec[1:] if plus else spec
        if ":" in s:
            src, dst = s.split(":", 1)
        else:
            src, dst = s, s
        if dst in ("HEAD", "@"):
            dst = branch or ""
        if dst.startswith("refs/heads/"):
            dst = dst[len("refs/heads/"):]
        if not dst or dst.startswith("refs/") or not _is_protected(dst, protected):
            continue
        if src == "" or info["delete"]:
            rewrites.append((dst, "delete"))
        elif plus or info["force"]:
            rewrites.append((dst, "force"))
        else:
            rewrites.append((dst, "push"))

    for how in ("delete", "force"):
        for dst, kind in rewrites:
            if kind != how:
                continue
            if how == "delete":
                return Block("git force-push", "deleting %s on the remote" % dst,
                             "An agent session doesn't remove a protected branch.")
            return Block("git force-push", "a force push to %s" % dst,
                         "Rewriting a protected branch can throw away other people's work.")
    if on_protected:
        return Block("git push", "`git push` from %s" % branch,
                     "Push a feature branch and open a pull request instead.")
    for dst, kind in rewrites:
        return Block("git push", "a push to %s" % dst,
                     "Changes reach a protected branch through a pull request, not a direct push.")
    return None


def _check_git(cmd, branches, protected):
    parsed = _parse_git(cmd.argv)
    if parsed is None:
        return None
    repo_opts, sub, args = parsed
    if sub in ("switch", "checkout"):
        branches.note_switch(cmd, repo_opts, sub, args, protected)
        return None
    wants_help = any(a in ("-h", "--help") for a in args)

    if sub == "stash":
        if wants_help or (args and args[0] in ("list", "show")):
            return None
        return Block("git stash", "`git stash`",
                     "All worktrees of a repository share one stash stack, so a parallel session can "
                     "pop your changes, or you can pop theirs. Commit to a temporary branch or use a "
                     "separate worktree instead.")

    if sub == "commit":
        if wants_help or "--dry-run" in args:
            return None
        branch = branches.get(cmd, repo_opts)
        if _is_protected(branch, protected):
            return Block("git commit", "`git commit` on %s" % branch,
                         "Create a feature branch first (git switch -c <name>, or a worktree from "
                         "origin/%s) and commit there." % branch)
        return None

    if sub == "merge":
        if wants_help or any(a in ("--abort", "--quit") for a in args):
            return None
        branch = branches.get(cmd, repo_opts)
        if _is_protected(branch, protected):
            return Block("git merge", "`git merge` on %s" % branch,
                         "Merge into a feature branch, or through a pull request.")
        return None

    if sub == "push":
        return _check_push(args, branches.get(cmd, repo_opts), protected)
    return None


# ---------------------------------------------------------- deploys

_KUBECTL_VALUE_OPTS = {
    "-n", "--namespace", "--context", "--kubeconfig", "-s", "--server", "--cluster", "--user",
    "--token", "--as", "--as-group", "--as-uid", "--request-timeout", "--certificate-authority",
    "--client-certificate", "--client-key", "--tls-server-name", "--cache-dir", "--password",
    "--username", "--profile", "--profile-output", "-v", "--v", "--vmodule", "--log-file",
    "--log-flush-frequency", "-l", "--selector",
}
_HELM_VALUE_OPTS = {
    "-n", "--namespace", "--kube-context", "--kubeconfig", "--registry-config",
    "--repository-cache", "--repository-config", "--burst-limit", "--qps", "--kube-apiserver",
    "--kube-as-user", "--kube-as-group", "--kube-ca-file", "--kube-tls-server-name",
    "--kube-token", "--content-cache",
}
_HELM_VERBS = {"upgrade": "upgrade", "install": "install", "uninstall": "uninstall",
               "un": "uninstall", "delete": "uninstall", "del": "uninstall", "rollback": "rollback"}
_KUBECTL_VERBS = {"apply", "delete", "scale", "edit", "patch"}


def _verb_index(args, value_opts):
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            return i + 1 if i + 1 < len(args) else None
        if a.startswith("-"):
            if "=" not in a and a in value_opts:
                i += 2
            else:
                i += 1
            continue
        return i
    return None


def _is_dry_run(args):
    for a in args:
        if a == "--dry-run":
            return True
        if a.startswith("--dry-run="):
            return a.split("=", 1)[1].lower() not in ("none", "false", "")
    return False


def _wants_help(args):
    return any(a in ("-h", "--help", "-help") for a in args)


_DEPLOY_REASON = ("Deploys and cluster changes need the user's go-ahead in this conversation, "
                  "so ask the user. Only the user can allow this rule, in .claude/executor-guard.json "
                  "or EXECUTOR_GUARD_ALLOW; don't change either yourself.")


def _check_deploy(cmd):
    name = cmd.name
    args = cmd.argv[1:]
    rule = None
    if name == "helm":
        i = _verb_index(args, _HELM_VALUE_OPTS)
        if i is not None and args[i] in _HELM_VERBS:
            rest = args[i + 1:]
            if not (_is_dry_run(rest) or _wants_help(rest)):
                rule = "helm " + _HELM_VERBS[args[i]]
    elif name in ("kubectl", "oc"):
        i = _verb_index(args, _KUBECTL_VALUE_OPTS)
        if i is not None:
            verb, rest = args[i], args[i + 1:]
            if _is_dry_run(rest) or _wants_help(rest):
                return None
            if verb in _KUBECTL_VERBS:
                if verb == "apply" and rest and rest[0] == "view-last-applied":
                    return None
                rule = "kubectl " + verb
            elif verb == "rollout":
                j = _verb_index(rest, _KUBECTL_VALUE_OPTS)
                if j is not None and rest[j] == "restart":
                    rule = "kubectl rollout restart"
    elif name in ("terraform", "tofu"):
        i = _verb_index(args, ())
        if i is not None and args[i] in ("apply", "destroy"):
            if not _wants_help(args[i + 1:]):
                rule = "%s %s" % (name, args[i])
    if rule is None:
        return None
    return Block(rule, "`%s`" % rule, _DEPLOY_REASON)


# ------------------------------------------------------------- main

def check(command, cwd, cfg):
    """Return the first Block for this command line, or None."""
    branches = _Branches()
    for cmd in shell_words.commands(command, cwd):
        found = None
        if cmd.name == "git":
            found = _check_git(cmd, branches, cfg.protected_branches)
        elif cmd.name in ("helm", "kubectl", "oc", "terraform", "tofu"):
            found = _check_deploy(cmd)
        if found is not None and not cfg.allows(found.rule):
            return found
    return None


def message(block, cfg):
    text = "executor-guard blocked %s. %s (rule: %s)" % (block.what, block.reason, block.rule)
    if cfg.error:
        text += "\nexecutor-guard could not read its config, so nothing is allowed by it: %s" % cfg.error
    return text


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if not isinstance(data, dict) or data.get("tool_name") not in (None, "Bash"):
        return 0
    tool_input = data.get("tool_input") or {}
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str) or not command.strip():
        return 0
    cwd = data.get("cwd") or os.getcwd()
    cfg = guard_config.load(cwd)
    block = check(command, cwd, cfg)
    if block is None:
        return 0
    sys.stderr.write(message(block, cfg) + "\n")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:  # never let a bug in the guard stop the session
        sys.exit(0)
