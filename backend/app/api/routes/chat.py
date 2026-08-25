import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from langchain_core.messages import HumanMessage
from sqlalchemy.orm import Session

from app.agents.graph import build_navi_graph
from app.api.deps import get_current_user
from app.core.audit import log_audit_event
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.care_journey import CareJourney, CareJourneyStep
from app.models.user import User
from app.schemas.chat import AgentStep, ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
@limiter.limit("20/minute")
def send_message(
    request: Request, payload: ChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    if payload.journey_id:
        journey = db.get(CareJourney, uuid.UUID(payload.journey_id))
        if not journey or journey.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Care journey not found")
    else:
        journey = CareJourney(user_id=user.id, title=payload.message[:80], original_request=payload.message)
        db.add(journey)
        db.commit()
        db.refresh(journey)

    log_audit_event(
        db, user_id=user.id, event_type="agent_invocation",
        description="Chat request routed through NAVI agent graph",
        metadata={"journey_id": str(journey.id)},
    )

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
            "contains_simulated_data": False,
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
        log_audit_event(
            db, user_id=user.id, event_type="escalation", agent_name="safety_agent",
            description="Safety agent escalated journey to human review",
            metadata={"flags": result.get("safety_flags", []), "journey_id": str(journey.id)},
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
        contains_simulated_data=result.get("contains_simulated_data", False),
    )
