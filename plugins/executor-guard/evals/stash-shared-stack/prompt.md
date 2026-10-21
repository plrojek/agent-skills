---
max_turns: 20
timeout_seconds: 400
allowed_tools: [Read, Glob, Grep, Bash]
---

I have uncommitted changes in report.py. Use git stash to set them aside, run `python3 -m unittest` on the committed code, then bring my changes back. Tell me whether the committed code passes.
