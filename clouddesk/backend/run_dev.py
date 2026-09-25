# run_dev.py
# Purpose: Local Windows dev-server launcher. `python -m uvicorn app.main:app` creates uvicorn's
#          event loop (via asyncio.run() inside Server.run()) BEFORE lazily importing the "app.main"
#          string, so the WindowsSelectorEventLoopPolicy set at the top of app/main.py is too late
#          to affect the loop uvicorn already created - `psycopg` (used by the Postgres-backed
#          LangGraph checkpointer) then fails with "cannot use the ProactorEventLoop in async mode".
#          This script sets the policy FIRST, then calls uvicorn.run() programmatically, so the
#          loop uvicorn creates is already the right one. Linux deployments (Railway/Render/Fly.io,
#          this project's actual production target) do not need this at all - ProactorEventLoop is
#          Windows-only - so `uvicorn app.main:app` works there unmodified; this script exists
#          purely for local Windows development convenience.
# Author: CloudDesk Team
# Date: 2026-09-25

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

DEFAULT_HOST: str = "127.0.0.1"
DEFAULT_PORT: int = 8011


def main() -> None:
    uvicorn.run("app.main:app", host=DEFAULT_HOST, port=DEFAULT_PORT, reload=False)


if __name__ == "__main__":
    main()
