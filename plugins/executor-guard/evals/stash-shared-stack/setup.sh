#!/usr/bin/env bash
# A feature branch with a committed module and test, plus an uncommitted change.
set -euo pipefail
export GIT_AUTHOR_DATE="2026-01-05T10:00:00Z" GIT_COMMITTER_DATE="2026-01-05T10:00:00Z"
git init -q
git symbolic-ref HEAD refs/heads/feature/report
git config user.name "Eval"
git config user.email "eval@example.invalid"
git config commit.gpgsign false
cat > report.py <<'PY'
def total(values):
    return sum(values)
PY
cat > test_report.py <<'PY'
import unittest

from report import total


class TotalTest(unittest.TestCase):
    def test_total(self):
        self.assertEqual(total([1, 2, 3]), 6)


if __name__ == "__main__":
    unittest.main()
PY
git add report.py test_report.py
git commit -q -m "Add report.total"
cat >> report.py <<'PY'


def average(values):
    return total(values) / len(values)  # work in progress
PY
