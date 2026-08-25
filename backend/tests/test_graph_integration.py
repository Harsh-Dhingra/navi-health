"""End-to-end test of the actual LangGraph wiring — supervisor routing, tool
execution, state threading, safety escalation — without calling a real LLM.

`_get_llm` is monkeypatched to a scripted fake that returns canned responses
in the exact shape each node expects. Everything else is real: the compiled
StateGraph, conditional routing between nodes, the RAG retriever hitting a
live Postgres+pgvector database, actual tool execution (the real
MockEligibilityProvider math and its `data_source` tagging), and the safety
agent's deterministic simulated-data disclaimer logic.

Requires a reachable Postgres with pgvector and `alembic upgrade head`
already applied (see backend/tests/conftest.py and
.github/workflows/backend-ci.yml). Skips cleanly if the database isn't
reachable, so it doesn't block running the rest of the suite offline.
"""

import json
import uuid

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import text

from app.db.session import SessionLocal


def _db_available() -> bool:
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1 FROM users LIMIT 1"))
        db.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_available(), reason="requires a live Postgres+pgvector with migrations applied"
)

SUPERVISOR_RESPONSE = json.dumps({"intent": "mri_navigation", "plan": ["insurance", "cost", "authorization"]})
SAFETY_RESPONSE = json.dumps(
    {"flags": [], "requires_human_review": False, "final_response": "Here is what I found about your MRI."}
)

# Which tool each domain agent "chooses" to call, keyed by node name.
DOMAIN_TOOL_CALLS = {
    "insurance": ("estimate_procedure_cost", {"procedure_code": "MRI-KNEE", "in_network": True, "deductible_remaining": 500}),
    "cost": ("estimate_procedure_cost", {"procedure_code": "MRI-KNEE", "in_network": True, "deductible_remaining": 200}),
    "authorization": ("check_prior_authorization_requirement", {"procedure_code": "MRI-KNEE", "payer_name": "Aetna"}),
}


class _FakeToolBoundLLM:
    """Stands in for `ChatAnthropic(...).bind_tools(...)` — first call proposes
    a tool call, second call (with the tool result appended) returns prose."""

    def __init__(self, tool_name, tool_args, follow_up_text):
        self._tool_name = tool_name
        self._tool_args = tool_args
        self._follow_up_text = follow_up_text
        self._calls = 0

    def invoke(self, _messages):
        self._calls += 1
        if self._calls == 1:
            return AIMessage(
                content="", tool_calls=[{"name": self._tool_name, "args": self._tool_args, "id": "call_1"}]
            )
        return AIMessage(content=self._follow_up_text)


class _FakePlainLLM:
    """Stands in for a bare `ChatAnthropic(...)` call (supervisor, safety)."""

    def __init__(self, response_text):
        self._response_text = response_text

    def invoke(self, _messages):
        return AIMessage(content=self._response_text)


class _FakeUnboundLLM:
    """Stands in for the raw `ChatAnthropic(...)` before `.bind_tools(...)` is
    called — domain-agent nodes do `_get_llm().bind_tools(ALL_TOOLS)`."""

    def __init__(self, tool_name, tool_args, follow_up_text):
        self._tool_name = tool_name
        self._tool_args = tool_args
        self._follow_up_text = follow_up_text

    def bind_tools(self, _tools):
        return _FakeToolBoundLLM(self._tool_name, self._tool_args, self._follow_up_text)


def _scripted_get_llm(monkeypatch, graph_module):
    """Node functions call _get_llm() in a fixed, known order: supervisor once,
    then once per planned domain agent, then safety once. Script responses in
    that order rather than trying to inspect which node is calling."""
    node_order = iter(["supervisor", "insurance", "cost", "authorization", "safety"])

    def fake_get_llm(temperature: float = 0.0):
        node = next(node_order)
        if node == "supervisor":
            return _FakePlainLLM(SUPERVISOR_RESPONSE)
        if node == "safety":
            return _FakePlainLLM(SAFETY_RESPONSE)
        tool_name, tool_args = DOMAIN_TOOL_CALLS[node]
        return _FakeUnboundLLM(tool_name, tool_args, follow_up_text=f"{node} summary based on real tool output")

    monkeypatch.setattr(graph_module, "_get_llm", fake_get_llm)


def test_full_graph_run_with_simulated_data_disclosed(monkeypatch):
    from app.agents import graph as graph_module

    _scripted_get_llm(monkeypatch, graph_module)

    db = SessionLocal()
    try:
        graph = graph_module.build_navi_graph(db)
        result = graph.invoke(
            {
                "messages": [HumanMessage("My doctor ordered an MRI for my knee")],
                "user_id": str(uuid.uuid4()),
                "journey_id": str(uuid.uuid4()),
                "intent": None,
                "plan": [],
                "insurance_result": None,
                "provider_result": None,
                "cost_result": None,
                "authorization_result": None,
                "safety_flags": [],
                "requires_human_review": False,
                "contains_simulated_data": False,
                "completed_steps": [],
                "final_response": None,
            }
        )
    finally:
        db.close()

    # The supervisor's plan was actually parsed and actually drove routing —
    # only insurance/cost/authorization ran, not provider.
    agent_names_run = {step["agent_name"] for step in result["completed_steps"]}
    assert agent_names_run == {"insurance_agent", "cost_agent", "authorization_agent", "safety_agent"}

    # Real tool execution happened: MockEligibilityProvider actually ran and
    # tagged its output, and the graph actually threaded that flag through to
    # the safety node's disclaimer logic — none of this is scripted above.
    assert result["contains_simulated_data"] is True
    assert "simulation" in result["final_response"].lower() or "simulated" in result["final_response"].lower()

    cost_tool_result = result["cost_result"]["tool_results"][0]
    assert cost_tool_result["data_source"] == "simulated"
    assert cost_tool_result["estimated_patient_responsibility"] > 0

    assert result["requires_human_review"] is False


def test_safety_agent_escalates_on_unparseable_response(monkeypatch):
    """If the safety agent's output can't be parsed, the graph must fail
    closed — escalate to a human — not silently show an unverified reply."""
    from app.agents import graph as graph_module

    node_order = iter(["supervisor", "insurance", "safety"])

    def fake_get_llm(temperature: float = 0.0):
        node = next(node_order)
        if node == "supervisor":
            return _FakePlainLLM(json.dumps({"intent": "mri_navigation", "plan": ["insurance"]}))
        if node == "safety":
            return _FakePlainLLM("not valid json at all")
        tool_name, tool_args = DOMAIN_TOOL_CALLS["insurance"]
        return _FakeUnboundLLM(tool_name, tool_args, follow_up_text="insurance summary")

    monkeypatch.setattr(graph_module, "_get_llm", fake_get_llm)

    db = SessionLocal()
    try:
        graph = graph_module.build_navi_graph(db)
        result = graph.invoke(
            {
                "messages": [HumanMessage("My doctor ordered an MRI")],
                "user_id": str(uuid.uuid4()),
                "journey_id": str(uuid.uuid4()),
                "intent": None,
                "plan": [],
                "insurance_result": None,
                "provider_result": None,
                "cost_result": None,
                "authorization_result": None,
                "safety_flags": [],
                "requires_human_review": False,
                "contains_simulated_data": False,
                "completed_steps": [],
                "final_response": None,
            }
        )
    finally:
        db.close()

    assert result["requires_human_review"] is True
    assert "safety_agent_output_unparseable" in result["safety_flags"]
