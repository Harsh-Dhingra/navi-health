import uuid

from fastapi import APIRouter, Depends
from langchain_core.messages import HumanMessage
from sqlalchemy.orm import Session

from app.agents.graph import build_navi_graph
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.care_journey import CareJourney, CareJourneyStep
from app.models.user import User
from app.schemas.chat import AgentStep, ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def send_message(payload: ChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.journey_id:
        journey = db.get(CareJourney, uuid.UUID(payload.journey_id))
    else:
        journey = CareJourney(user_id=user.id, title=payload.message[:80], original_request=payload.message)
        db.add(journey)
        db.commit()
        db.refresh(journey)

    graph = build_navi_graph(db)
    result = graph.invoke(
        {
            "messages": [HumanMessage(payload.message)],
            "user_id": str(user.id),
            "journey_id": str(journey.id),
            "intent": None,
            "plan": [],
            "insurance_result": None,
            "provider_result": None,
            "cost_result": None,
            "authorization_result": None,
            "safety_flags": [],
            "requires_human_review": False,
            "completed_steps": [],
            "final_response": None,
        }
    )

    for index, step in enumerate(result["completed_steps"]):
        db.add(
            CareJourneyStep(
                journey_id=journey.id,
                sequence=index,
                step_type=step["step_type"],
                agent_name=step["agent_name"],
                status=step["status"],
                data=step["data"],
                requires_human_review=step.get("requires_human_review", False),
            )
        )

    if result.get("requires_human_review"):
        journey.status = "escalated"
        db.add(
            AuditLog(
                user_id=user.id,
                event_type="escalation",
                agent_name="safety_agent",
                description="Safety agent escalated journey to human review",
                event_metadata={"flags": result.get("safety_flags", [])},
            )
        )
    else:
        journey.status = "completed"

    db.add(journey)
    db.commit()

    return ChatResponse(
        journey_id=str(journey.id),
        reply=result.get("final_response") or "I wasn't able to generate a response — please try again.",
        steps=[
            AgentStep(
                agent_name=s["agent_name"],
                step_type=s["step_type"],
                status=s["status"],
                data=s["data"],
                requires_human_review=s.get("requires_human_review", False),
            )
            for s in result["completed_steps"]
        ],
        safety_flags=result.get("safety_flags", []),
        escalated=result.get("requires_human_review", False),
    )
