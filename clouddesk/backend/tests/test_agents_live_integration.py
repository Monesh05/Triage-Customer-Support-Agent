# tests/test_agents_live_integration.py
# Purpose: ONE real end-to-end proof that the LLM wiring works against the configured provider
#          (per .env: LLM_PROVIDER/OPENAI_API_KEY/OPENAI_MODEL). Marked `integration` and
#          excluded from the default `pytest` run (see pytest.ini addopts) so the default suite
#          stays free and deterministic. Run explicitly with:
#              pytest -m integration tests/test_agents_live_integration.py -v -s
# Author: CloudDesk Team
# Date: 2026-09-24

import pytest

from app.agents.schemas import TriageResult
from app.agents.triage import run_triage_agent
from app.llm.structured import AgentError

pytestmark = pytest.mark.integration


async def test_triage_agent_live_call() -> None:
    """A single real call to the configured LLM, using the Triage Agent (cheapest, no tools)."""
    result = await run_triage_agent(
        "I upgraded to Pro yesterday, got charged twice, and now my API requests return 403."
    )

    assert not isinstance(result, AgentError), f"Live call failed: {result}"
    assert isinstance(result, TriageResult)
    assert result.intents
    assert result.priority in {"low", "medium", "high", "urgent"}
    print("\n--- LIVE TRIAGE AGENT OUTPUT ---")
    print(result.model_dump_json(indent=2))
