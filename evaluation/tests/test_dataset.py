# evaluation/tests/test_dataset.py
# Purpose: Validates evaluation/datasets/schema.py's `DatasetRecord` model and the generated
#          evaluation/datasets/tickets.jsonl dataset: schema validity, minimum size (spec
#          section 28: "at least 100"), full category coverage, and that every customer_id looks
#          like a real UUID (not a placeholder). Does NOT run the real graph/DB/LLM.
# Author: CloudDesk Team
# Date: 2026-09-24

import json
import os
import uuid

import pytest

from evaluation.datasets.schema import MIN_DATASET_SIZE, REQUIRED_CATEGORIES, DatasetRecord

DATASET_PATH = os.path.join(os.path.dirname(__file__), "..", "datasets", "tickets.jsonl")


def _load_records() -> list[DatasetRecord]:
    records: list[DatasetRecord] = []
    with open(DATASET_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(DatasetRecord.model_validate_json(line))
    return records


def test_dataset_record_schema_accepts_valid_record() -> None:
    record = DatasetRecord(
        ticket_id="t-1",
        category="billing",
        customer_id=str(uuid.uuid4()),
        customer_message="I was charged twice.",
        expected_intents=["billing"],
        expected_required_agents=["billing"],
        expected_priority="high",
        expected_escalation=False,
    )
    assert record.is_false_positive is False
    assert record.expect_qa_approval is None


def test_dataset_record_schema_rejects_unknown_category() -> None:
    with pytest.raises(ValueError):
        DatasetRecord(
            ticket_id="t-2",
            category="not-a-real-category",
            customer_id=str(uuid.uuid4()),
            customer_message="hi",
            expected_intents=["billing"],
            expected_required_agents=["billing"],
            expected_priority="high",
            expected_escalation=False,
        )


def test_dataset_file_exists_and_parses() -> None:
    assert os.path.exists(DATASET_PATH), "Run `python -m evaluation.datasets.generate` first."
    records = _load_records()
    assert len(records) > 0


def test_dataset_meets_minimum_size() -> None:
    records = _load_records()
    assert len(records) >= MIN_DATASET_SIZE


def test_dataset_covers_every_required_category() -> None:
    records = _load_records()
    seen_categories = {record.category for record in records}
    assert seen_categories == set(REQUIRED_CATEGORIES)


def test_dataset_ticket_ids_are_unique() -> None:
    records = _load_records()
    ticket_ids = [record.ticket_id for record in records]
    assert len(ticket_ids) == len(set(ticket_ids))


def test_dataset_customer_ids_are_valid_uuids() -> None:
    records = _load_records()
    for record in records:
        uuid.UUID(record.customer_id)  # raises ValueError if malformed


def test_dataset_raw_json_lines_are_valid() -> None:
    with open(DATASET_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                json.loads(line)
