# evaluation/__init__.py
# Purpose: Top-level package for Phase 8 (Evaluation, spec section 28). This package lives
#          OUTSIDE `clouddesk/backend/` (spec section 30's tree shows `evaluation/` as a sibling
#          of `clouddesk/`), but it needs to import and exercise the real backend application
#          (`app.graph.graph.run_support_workflow`, `app.services.observability_service`, etc.).
#          `clouddesk/backend/app` is a standalone application package (imported everywhere in
#          that codebase as plain `app.*`, not `clouddesk.backend.app.*`), not something installed
#          via pip. Rather than rewrite every backend import, this module inserts
#          `clouddesk/backend` onto `sys.path` the same way `clouddesk/data/seed/seed.py` already
#          does for the exact same reason (see that file's header) — so `import app...` resolves
#          to the real backend package regardless of the caller's current working directory. This
#          runs once, as a side effect of `import evaluation` (or `python -m evaluation.run_eval`,
#          which imports this package first), before any submodule does `from app... import ...`.
# Author: CloudDesk Team
# Date: 2026-09-24

import os
import sys

_EVALUATION_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_EVALUATION_DIR, ".."))
_BACKEND_DIR = os.path.join(_REPO_ROOT, "clouddesk", "backend")

for _path in (_BACKEND_DIR, _REPO_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)
