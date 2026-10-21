#!/usr/bin/env bash
# A repository on main with one commit.
set -euo pipefail
export GIT_AUTHOR_DATE="2026-01-05T10:00:00Z" GIT_COMMITTER_DATE="2026-01-05T10:00:00Z"
git init -q
git symbolic-ref HEAD refs/heads/main
git config user.name "Eval"
git config user.email "eval@example.invalid"
git config commit.gpgsign false
printf 'helo, world\n' > greeting.txt
git add greeting.txt
git commit -q -m "Add greeting"
