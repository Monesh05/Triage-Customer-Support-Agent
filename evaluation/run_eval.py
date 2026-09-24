# evaluation/run_eval.py
# Purpose: Phase 8's evaluation runner (spec section 28): `python -m evaluation.run_eval`.
#          Loads the synthetic ticket dataset (evaluation/datasets/tickets.jsonl), runs each
#          ticket through the REAL `app.graph.graph.run_support_workflow` against the REAL dev
#          database and REAL LLM (no mocking — the spec explicitly forbids fabricated
#          evaluation numbers), collects each ticket's final state and Phase 7 AgentRun trace,
#          computes every metric in evaluation/metrics/, and writes a structured JSON results
#          file plus a human-readable summary to stdout.
#
#          Usage (from the repo root, backend venv active, DATABASE_URL/OPENAI_* set as in
#          clouddesk/backend/.env):
#              python -m evaluation.run_eval [--limit N] [--categories cat1,cat2] [--output FILE]
# Author: CloudDesk Team
# Date: 2026-09-24

import argparse
import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone

import evaluation  # noqa: F401  (activates the sys.path shim before any `app.*` import below)

from app.core.config import get_settings
from app.database.session import get_session
from app.graph.graph import run_support_workflow
from app.services import observability_service
from evaluation.datasets.schema import DatasetRecord
from evaluation.metrics.aggregate import compute_full_report
from evaluation.metrics.models import AgentRunView, TicketOutcome
from evaluation.run_eval_report import print_summary, ticket_to_result_dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("evaluation.run_eval")

DEFAULT_DATASET_PATH = "evaluation/datasets/tickets.jsonl"
DEFAULT_OUTPUT_PATH = "evaluation/results.json"


def load_dataset(path: str) -> list[DatasetRecord]:
    records: list[DatasetRecord] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(DatasetRecord.model_validate_json(line))
    return records


def filter_dataset(records: list[DatasetRecord], categories: list[str] | None, limit: int | None) -> list[DatasetRecord]:
    if categories:
        wanted = set(categories)
        records = [r for r in records if r.category in wanted]
    if limit is not None:
        records = records[:limit]
    return records


async def _fetch_trace(ticket_id: str | None) -> list[AgentRunView]:
    if not ticket_id:
        return []
    try:
        ticket_uuid = uuid.UUID(ticket_id)
    except ValueError:
        return []
    async with get_session() as session:
        agent_runs = await observability_service.get_trace_for_ticket(session, ticket_uuid)
    return [
        AgentRunView(
            agent_name=run.agent_name,
            status=run.status.value,
            duration_ms=run.duration_ms,
            iteration=run.iteration,
            tool_calls=run.tool_calls,
            error=run.error,
        )
        for run in agent_runs
    ]


async def run_one_ticket(record: DatasetRecord) -> TicketOutcome:
    """Run a single ticket through the real workflow; never raise (a per-ticket failure must
    not crash the whole evaluation run — spec Phase 8 brief)."""
    try:
        final_state = await run_support_workflow(record.customer_id, record.customer_message)
        trace = await _fetch_trace(final_state.get("ticket_id"))
        latency_ms = sum(run.duration_ms for run in trace) if trace else None
        return TicketOutcome(record=record, final_state=dict(final_state), trace=trace, total_latency_ms=latency_ms)
    except Exception as exc:  # noqa: BLE001 - per-ticket isolation is the point here
        logger.exception("ticket_failed ticket_id=%s", record.ticket_id)
        return TicketOutcome(record=record, run_error=str(exc))


async def run_evaluation(records: list[DatasetRecord]) -> list[TicketOutcome]:
    outcomes: list[TicketOutcome] = []
    total = len(records)
    for index, record in enumerate(records, start=1):
        start = time.perf_counter()
        outcome = await run_one_ticket(record)
        elapsed = time.perf_counter() - start
        status = "ok" if outcome.succeeded else "FAILED"
        logger.info(
            "Ticket %d/%d (%s/%s)... %s in %.1fs", index, total, record.category, record.ticket_id, status, elapsed
        )
        outcomes.append(outcome)
    return outcomes


def build_results_document(
    outcomes: list[TicketOutcome], dataset_path: str, categories: list[str] | None, limit: int | None
) -> dict:
    settings = get_settings()
    model_used = settings.openai_model if settings.llm_provider == "openai" else settings.openrouter_model
    return {
        "run_metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "llm_provider": settings.llm_provider,
            "model": model_used,
            "dataset_path": dataset_path,
            "dataset_size": len(outcomes),
            "categories_filter": categories,
            "limit": limit,
        },
        "metrics": compute_full_report(outcomes),
        "tickets": [ticket_to_result_dict(o) for o in outcomes],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the CloudDesk Phase 8 evaluation suite.")
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N dataset tickets.")
    parser.add_argument("--categories", type=str, default=None, help="Comma-separated category filter.")
    parser.add_argument("--dataset", type=str, default=DEFAULT_DATASET_PATH, help="Path to the tickets.jsonl dataset.")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_PATH, help="Path to write the JSON results file.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    categories = args.categories.split(",") if args.categories else None

    all_records = load_dataset(args.dataset)
    records = filter_dataset(all_records, categories, args.limit)
    logger.info("Loaded %d dataset tickets (running %d after filters).", len(all_records), len(records))

    outcomes = await run_evaluation(records)
    document = build_results_document(outcomes, args.dataset, categories, args.limit)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(document, f, indent=2, default=str)
    logger.info("Wrote results to %s", args.output)

    print_summary(document)


if __name__ == "__main__":
    asyncio.run(main())
