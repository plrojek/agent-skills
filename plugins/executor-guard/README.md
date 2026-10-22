# executor-guard

Hooks for Claude Code sessions that carry out a plan: no commits, merges or pushes on `main`, no force pushes to it, no `git stash`, no deploys without your OK, and a nudge to run the tests before stopping. Plus `/executor-guard:handoff`.

```
/plugin marketplace add plrojek/agent-skills
/plugin install executor-guard@plrojek
```

For bigger pieces of work I split the job in two: one session investigates and writes a plan, another session, often on a cheaper model, carries out one slice of it under a page of hard rules. Some of those rules can be checked by a script instead of trusted to the model, and this plugin turns them into hooks.

A hook that runs before every Bash command blocks:

- `git commit`, `git merge` and `git push` while the current branch is `main` or `master`, and a push straight to either of them from another branch;
- force pushes to `main` or `master`, and deleting them on the remote;
- `git stash`, apart from `list` and `show`. All worktrees of a repository share one stash stack, so with agents working in parallel one of them can pop another's changes;
- `helm upgrade`, `install`, `uninstall` and `rollback`; `kubectl apply`, `delete`, `rollout restart`, `scale`, `edit` and `patch`; `terraform` or `tofu` `apply` and `destroy`. Dry runs go through.

Claude gets the reason as the command's error, so it can make a branch, or stop and ask.

When Claude is about to finish, a second hook looks at the turn. If files were changed and no test or build command ran after the last change, it sends Claude back once, to run the tests and paste the output or to say plainly that it didn't. Changes to Markdown and text files don't count, and neither do files under `~/.claude` or temp directories outside the project. pytest, `go test`, `npm test`, `cargo test`, gradle, `xcodebuild test`, `make test` and a few dozen others count as tests; the list is at the top of `hooks/require_tests.py`. A run whose output says the runner never started (`command not found`, `No module named pytest`) doesn't count.

`/executor-guard:handoff [path]` writes a note for the next session, `HANDOFF.md` by default: what was planned, what's done with the evidence, what's not, open questions and the next step.

To allow something, add `.claude/executor-guard.json` to the project:

```json
{
  "allow": ["helm upgrade", "kubectl apply"],
  "protected_branches": ["main", "master", "release/*"],
  "test_commands": ["./scripts/check.sh"],
  "ignore_paths": ["docs/*"]
}
```

or start Claude with `EXECUTOR_GUARD_ALLOW="helm upgrade,kubectl apply"`. An entry covers every rule that starts with its words, so `"kubectl"` allows all the kubectl ones. Besides the deploy commands above, the rules are `git commit`, `git merge`, `git push`, `git force-push` and `git stash`, and each block message names the rule that fired. The hook can't see the conversation, so a deploy you OK in the chat still has to be allowed here first.

It catches mistakes; it isn't a security boundary. Things to know:

- It splits the command with Python's `shlex` and follows `&&` and `;`, pipes, subshells, `$( )`, `cd`, `env`, `sudo`, a shell started with `-c`, and heredocs. It doesn't expand variables or aliases, doesn't read scripts the command runs, and misses `$( )` and backticks inside double quotes. A command it can't parse, such as one with an unterminated quote, goes through.
- A quoted argument that is exactly an operator, like `echo "&&"`, is read as an operator.
- After `git checkout <branch>` in the same command line, the branch counts as unknown, and an unknown branch isn't checked.
- `git pull`, `rebase`, `cherry-pick`, `revert` and `am` on `main` aren't checked, and neither are `kubectl create`, `replace`, `set` or `rollout undo`, `gh pr merge`, or anything run over ssh.
- Claude can still write the config file itself, or edit files through Bash (`sed -i`, a heredoc into a file). The test check doesn't see edits made through Bash or by subagents, and it only looks at the current turn.
- Only the Bash tool is checked, not PowerShell on Windows.
- It needs `python3` (3.9 or later) on PATH. If a hook can't start, Claude Code carries on without it.

The tests are plain unittest and live outside the plugin, so they aren't installed: `python3 -m unittest discover -s tests/executor-guard` from the repository root. `plugins/executor-guard/evals/` has six cases for `claude plugin eval`; their setup scripts only write inside each case's own folder. The git cases need a git that works inside Claude Code's sandbox. On a Mac where the only git is Apple's `/usr/bin/git` it doesn't (xcrun can't write its cache there), so those cases pass without the hook ever being reached.

## What it runs and sends

- Two hooks, both local Python scripts started with `python3`: `hooks/guard_bash.py` before every Bash command and `hooks/require_tests.py` when Claude is about to stop. They read the command or the turn that Claude Code passes them, and `.claude/executor-guard.json` in the project if it exists.
- Nothing is downloaded, installed or sent anywhere. The hooks make no network requests and keep no data between runs.
- `/executor-guard:handoff` writes one Markdown file in the project, `HANDOFF.md` unless you give another path.

## License

MIT. Source: [github.com/plrojek/agent-skills](https://github.com/plrojek/agent-skills).
