---
description: Write a short handoff note for the next session - what was planned, what's done (with evidence), what's not, open questions
argument-hint: "[path, default HANDOFF.md]"
disable-model-invocation: true
allowed-tools: Read, Write, Glob, Grep, Bash(git status *), Bash(git log *), Bash(git diff *), Bash(git branch *), Bash(git rev-parse *)
---

Write a handoff note for whoever picks this work up next: another session, maybe on a cheaper model, that has none of this conversation.

Where to save it: $ARGUMENTS

If no path is given there, save it to `HANDOFF.md` at the top of the repository you're working in (`git rev-parse --show-toplevel`), or in the current directory if you're not in a repository.

Collect the facts before writing; don't write from memory alone.

1. Go back through this conversation for the task or plan you were given, the commands you ran and what they printed.
2. Run `git status --short`, `git branch --show-current`, `git log --oneline -10` and `git diff --stat`. If `origin/main` exists, also `git diff --stat origin/main...HEAD`.
3. If the file is already there, read it. Replace it unless the user asked you to add to it.

Then write the note with these sections, in this order:

```
# Handoff: <the task in one line>

<date, repository path, branch, last commit hash>

## Planned
What the task or plan asked for, in a few bullets. Name the plan file if there is one.

## Done
One bullet per finished piece, each with its evidence: a commit hash, a PR number, or the
command you ran and the line of output that shows it worked, for example
`go test ./...` -> `ok  example.com/pkg  0.41s`. Something that was changed but never
tested or built goes here only with the words "not tested".

## Not done
What's left, including work that was started and stopped, and where it stopped (file,
function, failing test). Uncommitted changes go here, with the files from git status.

## Open questions
Decisions you couldn't make, places where the code didn't match the plan, and things the
user has to check by hand (on a device, in a browser, in production). Write each one as a
question someone can answer.

## Next step
The first concrete thing the next session should do.
```

Rules for the note:

- Short plain statements. No praise and no summary of how well it went.
- Don't say a test passed, a build worked or a deploy happened unless its output is in this conversation. If you don't know, write "unknown" or "not checked".
- No secrets, tokens or passwords, even if they showed up in the session.
- Keep it under about 80 lines.

When it's saved, reply with the path and one line on what's in it.
