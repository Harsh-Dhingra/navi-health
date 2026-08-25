import uuid

from fastapi import FastAPI, Request, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes import account, auth, care_journey, chat, documents
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import limiter

settings = get_settings()
configure_logging(json_logs=settings.environment != "development")
logger = get_logger(__name__)

app = FastAPI(title=settings.app_name, version="0.1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.environment != "development":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


def _cors_headers_for(request: Request) -> dict[str, str]:
    """Starlette's ServerErrorMiddleware sits OUTSIDE CORSMiddleware, so a response
    built by an `Exception`-level handler (as opposed to a normal route response)
    never passes through CORSMiddleware and ships with no CORS headers — the
    browser then reports a CORS failure instead of surfacing our clean 500, which
    is exactly what a real cross-origin smoke test caught. Recompute the same
    headers CORSMiddleware would have added, for this response only."""
    origin = request.headers.get("origin")
    if origin and origin in settings.cors_origins:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin",
        }
    return {}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never leak stack traces or internal errors — especially with PHI in
    # request bodies/context — into an HTTP response.
    logger.error("unhandled_exception", path=request.url.path, error_type=type(exc).__name__)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
        headers=_cors_headers_for(request),
    )


@app.exception_handler(HTTPException)
async def logged_http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code >= 500:
        logger.error("http_exception", path=request.url.path, status_code=exc.status_code)
    return await http_exception_handler(request, exc)


app.include_router(auth.router)
app.include_router(account.router)
app.include_router(chat.router)
app.include_router(care_journey.router)
app.include_router(documents.router)


@app.get("/api/health")
def health_check():
    """Liveness probe — process is up. Does not touch the database."""
    return {"status": "ok", "service": settings.app_name}


@app.get("/api/ready")
def readiness_check():
    """Readiness probe — dependencies (DB) are reachable. Used by the
    deployment platform to gate traffic during rollout."""
    from sqlalchemy import text

    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "not_ready"})
    finally:
        db.close()
