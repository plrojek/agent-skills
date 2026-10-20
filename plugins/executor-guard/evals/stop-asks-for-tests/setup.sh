#!/usr/bin/env bash
# A tiny Python module with unittest tests, on a feature branch.
set -euo pipefail
export GIT_AUTHOR_DATE="2026-01-05T10:00:00Z" GIT_COMMITTER_DATE="2026-01-05T10:00:00Z"
git init -q
git symbolic-ref HEAD refs/heads/feature/calc
git config user.name "Eval"
git config user.email "eval@example.invalid"
git config commit.gpgsign false
cat > calc.py <<'PY'
def add(a, b):
    return a + b
PY
cat > test_calc.py <<'PY'
import unittest

from calc import add


class AddTest(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(add(2, 3), 5)

    def test_floats(self):
        self.assertAlmostEqual(add(0.1, 0.2), 0.3)


if __name__ == "__main__":
    unittest.main()
PY
git add calc.py test_calc.py
git commit -q -m "Add calc.add"
