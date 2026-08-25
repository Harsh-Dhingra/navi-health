from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit import log_audit_event
from app.core.config import get_settings
from app.core.security import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME, verify_password
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/api/account", tags=["account"])
settings = get_settings()


class DeleteAccountRequest(BaseModel):
    password: str


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(
    payload: DeleteAccountRequest,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Right-to-deletion: permanently removes the account and all associated
    PHI (insurance policies, claims, medications, visits, documents, care
    journeys cascade via FK). Requires re-entering the password so a hijacked
    session can't silently destroy data. Audit log entries are retained
    (user_id set null) as the compliance record of the deletion itself."""
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")

    log_audit_event(db, user_id=None, event_type="account_deleted", description=f"Account {user.id} deleted by owner")

    db.delete(user)
    db.commit()

    response.delete_cookie(ACCESS_COOKIE_NAME, path="/", domain=settings.cookie_domain)
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/", domain=settings.cookie_domain)
