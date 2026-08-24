from typing import Any

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    journey_id: str | None = None


class AgentStep(BaseModel):
    agent_name: str
    step_type: str
    status: str
    data: dict[str, Any] = {}
    requires_human_review: bool = False


class ChatResponse(BaseModel):
    journey_id: str
    reply: str
    steps: list[AgentStep]
    safety_flags: list[str] = []
    escalated: bool = False
