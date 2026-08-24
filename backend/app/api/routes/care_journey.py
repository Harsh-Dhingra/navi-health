import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.care_journey import CareJourney
from app.models.user import User
from app.schemas.care_journey import CareJourneyOut

router = APIRouter(prefix="/api/care-journeys", tags=["care-journeys"])


@router.get("", response_model=list[CareJourneyOut])
def list_journeys(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    journeys = db.scalars(
        select(CareJourney).where(CareJourney.user_id == user.id).order_by(CareJourney.created_at.desc())
    ).all()
    return journeys


@router.get("/{journey_id}", response_model=CareJourneyOut)
def get_journey(journey_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    journey = db.get(CareJourney, uuid.UUID(journey_id))
    if not journey or journey.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Care journey not found")
    return journey
