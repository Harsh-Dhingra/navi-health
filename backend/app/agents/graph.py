"""The NAVI multi-agent LangGraph workflow.

supervisor -> {insurance, provider, cost, authorization}* -> safety -> END

The supervisor classifies intent and builds a plan of which specialist
agents are relevant. Each specialist agent retrieves only the health
context it's scoped to (see app.rag.retriever), optionally calls domain
tools, and writes a structured result. The safety agent is the mandatory
final checkpoint: it screens every result for hallucination, groundedness,
sensitive-data exposure, and medical risk before anything reaches the
member, escalating to a human instead of answering when it isn't confident.
"""

import functools
import json
import re
import uuid
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agents import prompts
from app.agents.domain_tools import (
    check_prior_authorization_requirement,
    estimate_procedure_cost,
    search_in_network_providers,
)
from app.agents.state import NaviState
from app.core.config import get_settings
from app.rag.retriever import HealthContextRetriever

AGENT_ORDER = ["insurance", "provider", "cost", "authorization"]
ALL_TOOLS = [search_in_network_providers, estimate_procedure_cost, check_prior_authorization_requirement]
TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}

AGENT_PROMPTS = {
    "insurance": prompts.INSURANCE_SYSTEM_PROMPT,
    "provider": prompts.PROVIDER_SYSTEM_PROMPT,
    "cost": prompts.COST_SYSTEM_PROMPT,
    "authorization": prompts.AUTHORIZATION_SYSTEM_PROMPT,
}


def _get_llm(temperature: float = 0.0) -> ChatAnthropic:
    settings = get_settings()
    return ChatAnthropic(model=settings.anthropic_model, api_key=settings.anthropic_api_key, temperature=temperature)


def _extract_json(text: str) -> dict[str, Any]:
    """Strip markdown code fences a model may wrap JSON in, then parse."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def supervisor_node(state: NaviState) -> dict:
    llm = _get_llm()
    request_text = state["messages"][-1].content
    response = llm.invoke([SystemMessage(prompts.SUPERVISOR_SYSTEM_PROMPT), HumanMessage(request_text)])
    try:
        parsed = _extract_json(response.content)
        plan = [a for a in parsed.get("plan", []) if a in AGENT_ORDER]
        intent = parsed.get("intent", "healthcare_navigation")
    except Exception:
        plan, intent = list(AGENT_ORDER), "healthcare_navigation"
    return {"intent": intent, "plan": plan or list(AGENT_ORDER)}


def _run_domain_agent(state: NaviState, *, db: Session, scope: str, agent_label: str) -> dict:
    retriever = HealthContextRetriever(db)
    request_text = state["messages"][0].content
    context = retriever.retrieve(user_id=uuid.UUID(state["user_id"]), scope=scope, query=request_text)

    system_prompt = AGENT_PROMPTS[scope].format(context=context.to_prompt_context())
    messages: list = [SystemMessage(system_prompt), HumanMessage(request_text)]

    llm = _get_llm().bind_tools(ALL_TOOLS)
    ai_message: AIMessage = llm.invoke(messages)

    tool_results = []
    if ai_message.tool_calls:
        tool_messages = []
        for call in ai_message.tool_calls:
            tool = TOOLS_BY_NAME.get(call["name"])
            result = tool.invoke(call["args"]) if tool else {"error": f"unknown tool {call['name']}"}
            tool_results.append(result)
            tool_messages.append(ToolMessage(content=json.dumps(result, default=str), tool_call_id=call["id"]))
        follow_up = llm.invoke(messages + [ai_message] + tool_messages)
        summary = follow_up.content
    else:
        summary = ai_message.content

    result = {"summary": summary, "tool_results": tool_results}
    step = {
        "agent_name": agent_label,
        "step_type": scope,
        "status": "completed",
        "data": result,
        "requires_human_review": False,
    }
    return {f"{scope}_result": result, "completed_steps": [step]}


def safety_node(state: NaviState) -> dict:
    llm = _get_llm()
    payload = json.dumps(
        {
            "intent": state.get("intent"),
            "insurance_result": state.get("insurance_result"),
            "provider_result": state.get("provider_result"),
            "cost_result": state.get("cost_result"),
            "authorization_result": state.get("authorization_result"),
        },
        default=str,
    )
    response = llm.invoke([SystemMessage(prompts.SAFETY_SYSTEM_PROMPT), HumanMessage(payload)])
    try:
        parsed = _extract_json(response.content)
    except Exception:
        parsed = {
            "flags": ["safety_agent_output_unparseable"],
            "requires_human_review": True,
            "final_response": "I wasn't able to safely verify this response — routing to a human specialist.",
        }

    step = {
        "agent_name": "safety_agent",
        "step_type": "safety_review",
        "status": "completed",
        "data": {"flags": parsed.get("flags", [])},
        "requires_human_review": parsed.get("requires_human_review", False),
    }
    return {
        "safety_flags": parsed.get("flags", []),
        "requires_human_review": parsed.get("requires_human_review", False),
        "final_response": parsed.get("final_response"),
        "completed_steps": [step],
    }


def _route_from(current: str | None):
    """Build a router that sends state to the next planned agent after `current`, or to safety."""

    def router(state: NaviState) -> str:
        plan = state.get("plan") or list(AGENT_ORDER)
        start_index = AGENT_ORDER.index(current) + 1 if current else 0
        for candidate in AGENT_ORDER[start_index:]:
            if candidate in plan:
                return candidate
        return "safety"

    return router


def build_navi_graph(db: Session):
    graph = StateGraph(NaviState)
    graph.add_node("supervisor", supervisor_node)
    for agent in AGENT_ORDER:
        graph.add_node(agent, functools.partial(_run_domain_agent, db=db, scope=agent, agent_label=f"{agent}_agent"))
    graph.add_node("safety", safety_node)

    graph.set_entry_point("supervisor")
    routing_map = {**{a: a for a in AGENT_ORDER}, "safety": "safety"}
    graph.add_conditional_edges("supervisor", _route_from(None), routing_map)
    for agent in AGENT_ORDER:
        graph.add_conditional_edges(agent, _route_from(agent), routing_map)
    graph.add_edge("safety", END)

    return graph.compile()
