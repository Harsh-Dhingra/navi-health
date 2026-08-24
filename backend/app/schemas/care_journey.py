from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CareJourneyStepOut(BaseModel):
    id: str
    sequence: int
    step_type: str
    agent_name: str
    status: str
    data: dict[str, Any]
    requires_human_review: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CareJourneyOut(BaseModel):
    id: str
    title: str
    original_request: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    steps: list[CareJourneyStepOut] = []

    model_config = {"from_attributes": True}
