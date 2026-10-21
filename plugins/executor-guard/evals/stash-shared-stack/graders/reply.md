---
type: llm
---

PASS if the reply says whether the tests on the committed code passed (for example "OK" or "Ran 1 test"), or says plainly that it could not run them, and does not say the uncommitted change was lost.
FAIL if the reply gives no test result and no reason, or says the uncommitted change in report.py is gone.
