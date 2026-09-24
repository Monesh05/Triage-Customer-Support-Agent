# evaluation/tests/conftest.py
# Purpose: Ensures the repo root is on sys.path so `import evaluation...` resolves regardless
#          of how pytest is invoked (e.g. `pytest evaluation/tests/` from the repo root). These
#          tests deliberately exercise only dependency-free modules (dataset schema, metric
#          functions) — no `app.*` import, no database, no LLM call — so `evaluation/__init__`'s
#          backend sys.path shim is not needed here.
# Author: CloudDesk Team
# Date: 2026-09-24

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
