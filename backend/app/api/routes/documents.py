import re
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit import log_audit_event
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import SessionLocal, get_db
from app.models.document import Document
from app.models.user import User
from app.services.document_intelligence import process_document

router = APIRouter(prefix="/api/documents", tags=["documents"])
settings = get_settings()

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
ALLOWED_CONTENT_TYPES = {"application/pdf", "image/png", "image/jpeg"}
_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")


def _safe_filename(filename: str) -> str:
    name = Path(filename or "upload").name  # strips any directory components
    return _UNSAFE_CHARS.sub("_", name)[:255] or "upload"


def _process_document_task(document_id: uuid.UUID) -> None:
    """Runs after the request's DB session has closed, so it opens its own."""
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document:
            process_document(db, document)
    finally:
        db.close()


@router.post("/upload")
@limiter.limit("10/minute")
def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile,
    document_type: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    safe_name = _safe_filename(file.filename)
    extension = Path(safe_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS or file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    contents = file.file.read(max_bytes + 1)
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_size_mb}MB limit",
        )

    storage_dir = Path(settings.document_storage_path) / str(user.id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    destination = storage_dir / f"{uuid.uuid4()}_{safe_name}"
    destination.write_bytes(contents)

    document = Document(
        user_id=user.id,
        filename=safe_name,
        storage_path=str(destination),
        document_type=document_type,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    log_audit_event(
        db, user_id=user.id, event_type="document_uploaded",
        description="Member uploaded a source document", metadata={"document_id": str(document.id)},
    )

    background_tasks.add_task(_process_document_task, document.id)

    return {"id": str(document.id), "filename": document.filename, "status": "processing"}


@router.get("")
def list_documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    documents = db.scalars(select(Document).where(Document.user_id == user.id)).all()
    return [
        {
            "id": str(d.id),
            "filename": d.filename,
            "document_type": d.document_type,
            "processed": d.processed,
            "uploaded_at": d.uploaded_at,
        }
        for d in documents
    ]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = db.get(Document, uuid.UUID(document_id))
    if not document or document.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    Path(document.storage_path).unlink(missing_ok=True)
    db.delete(document)
    log_audit_event(
        db, user_id=user.id, event_type="document_deleted",
        description="Member deleted a source document", metadata={"document_id": document_id},
    )
