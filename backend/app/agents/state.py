import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage


class NaviState(TypedDict):
    """Shared state threaded through the LangGraph multi-agent workflow."""

    messages: Annotated[list[BaseMessage], operator.add]
    user_id: str
    journey_id: str

    # Router output
    intent: str | None
    plan: list[str]

    # Per-agent outputs, keyed by agent name -> structured result
    insurance_result: dict[str, Any] | None
    provider_result: dict[str, Any] | None
    cost_result: dict[str, Any] | None
    authorization_result: dict[str, Any] | None

    # Safety agent output
    safety_flags: list[str]
    requires_human_review: bool
    contains_simulated_data: bool

    # Bookkeeping
    completed_steps: Annotated[list[dict[str, Any]], operator.add]
    final_response: str | None
