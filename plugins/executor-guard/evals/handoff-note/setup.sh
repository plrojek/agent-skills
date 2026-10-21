#!/usr/bin/env bash
# A plan with three steps: step 1 committed, step 2 uncommitted, step 3 not started.
# Fixed dates keep the commit hashes the same on every run.
set -euo pipefail
export GIT_AUTHOR_DATE="2026-01-05T10:00:00Z" GIT_COMMITTER_DATE="2026-01-05T10:00:00Z"
git init -q
git symbolic-ref HEAD refs/heads/feature/csv-export
git config user.name "Eval"
git config user.email "eval@example.invalid"
git config commit.gpgsign false
cat > PLAN.md <<'MD'
# Plan: CSV export

1. Add `to_rows()` to `export.py` that turns orders into lists of strings.
2. Add `write_csv(path, orders)` in `csv_writer.py` using the csv module.
3. Add tests for both in `test_export.py`.
MD
cat > export.py <<'PY'
def to_rows(orders):
    return [[str(o["id"]), o["customer"], "%.2f" % o["total"]] for o in orders]
PY
git add PLAN.md export.py
git commit -q -m "Add to_rows for CSV export"
cat > csv_writer.py <<'PY'
import csv

from export import to_rows


def write_csv(path, orders):
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        # header row still missing
        writer.writerows(to_rows(orders))
PY
