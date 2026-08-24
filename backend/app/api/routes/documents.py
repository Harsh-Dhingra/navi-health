import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import SessionLocal, get_db
from app.models.document import Document
from app.models.user import User
from app.services.document_intelligence import process_document

router = APIRouter(prefix="/api/documents", tags=["documents"])
settings = get_settings()


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
def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    document_type: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    storage_dir = Path(settings.document_storage_path) / str(user.id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    destination = storage_dir / f"{uuid.uuid4()}_{file.filename}"
    destination.write_bytes(file.file.read())

    document = Document(
        user_id=user.id,
        filename=file.filename,
        storage_path=str(destination),
        document_type=document_type,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

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
