from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import log_audit_event
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.security import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db.session import get_db
from app.models.refresh_token import RefreshToken
from app.models.user import LOCKOUT_MINUTES, MAX_FAILED_LOGIN_ATTEMPTS, User
from app.schemas.auth import UserCreate, UserLogin, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    common = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "domain": settings.cookie_domain,
        "path": "/",
    }
    response.set_cookie(
        ACCESS_COOKIE_NAME, access_token, max_age=settings.jwt_access_expire_minutes * 60, **common
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=settings.jwt_refresh_expire_days * 24 * 60 * 60,
        **common,
    )


def _issue_session(db: Session, response: Response, user: User) -> None:
    access_token = create_access_token(str(user.id))
    raw_refresh, refresh_hash, expires_at = generate_refresh_token()
    db.add(RefreshToken(user_id=user.id, token_hash=refresh_hash, expires_at=expires_at))
    db.commit()
    _set_auth_cookies(response, access_token, raw_refresh)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_auth)
def register(request: Request, payload: UserCreate, response: Response, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    password_bytes = len(payload.password.encode("utf-8"))
    if len(payload.password) < 12:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must be at least 12 characters"
        )
    if password_bytes > 72:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must be at most 72 bytes"
        )

    user = User(email=payload.email, hashed_password=hash_password(payload.password), full_name=payload.full_name)
    db.add(user)
    db.commit()
    db.refresh(user)

    log_audit_event(db, user_id=user.id, event_type="account_created", description="User registered")
    _issue_session(db, response, user)
    return UserOut(id=str(user.id), email=user.email, full_name=user.full_name)


@router.post("/login", response_model=UserOut)
@limiter.limit(settings.rate_limit_auth)
def login(request: Request, payload: UserLogin, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))

    if user and user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked after too many failed attempts. Try again later.",
        )

    if not user or not user.is_active or not verify_password(payload.password, user.hashed_password):
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
                log_audit_event(
                    db, user_id=user.id, event_type="account_locked",
                    description=f"Locked after {MAX_FAILED_LOGIN_ATTEMPTS} failed login attempts",
                )
            db.add(user)
            db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    user.failed_login_attempts = 0
    user.locked_until = None
    db.add(user)
    db.commit()

    log_audit_event(db, user_id=user.id, event_type="login", description="User logged in")
    _issue_session(db, response, user)
    return UserOut(id=str(user.id), email=user.email, full_name=user.full_name)


@router.post("/refresh", response_model=UserOut)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    token_hash = hash_refresh_token(raw_refresh)
    record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if (
        not record
        or record.revoked
        or record.expires_at < datetime.now(timezone.utc)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalid or expired")

    user = db.get(User, record.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not available")

    # Rotate: revoke the used refresh token and issue a new one.
    record.revoked = True
    db.add(record)
    db.commit()
    _issue_session(db, response, user)
    return UserOut(id=str(user.id), email=user.email, full_name=user.full_name)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_refresh:
        token_hash = hash_refresh_token(raw_refresh)
        record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        if record:
            record.revoked = True
            db.add(record)
            db.commit()

    response.delete_cookie(ACCESS_COOKIE_NAME, path="/", domain=settings.cookie_domain)
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/", domain=settings.cookie_domain)
