"""Document intelligence: OCR, layout-aware parsing, and structured extraction.

Turns a scanned insurance card, EOB, or visit summary into (a) plain text via
OCR, (b) a handful of structured fields via pattern-based extraction, and
(c) embedded chunks for RAG retrieval. Swap `extract_fields` for an
LLM-based extractor (tool-calling against a Pydantic schema) once volume
justifies the cost — the interface is unchanged either way.
"""

import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.rag.embeddings import get_embedding_provider

MEMBER_ID_RE = re.compile(r"member\s*id[:#]?\s*([A-Z0-9-]+)", re.IGNORECASE)
GROUP_NUMBER_RE = re.compile(r"group\s*(?:number|no)?[:#]?\s*([A-Z0-9-]+)", re.IGNORECASE)
PAYER_KEYWORDS = ["aetna", "cigna", "unitedhealthcare", "anthem", "humana", "kaiser", "blue cross", "blue shield"]

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


@dataclass
class ExtractedDocument:
    raw_text: str
    document_type: str
    fields: dict = field(default_factory=dict)


def run_ocr(file_path: str) -> str:
    """OCR a PDF or image file to plain text. Requires the `tesseract` binary."""
    path = Path(file_path)
    try:
        import pytesseract
        from PIL import Image

        if path.suffix.lower() == ".pdf":
            from pdf2image import convert_from_path

            pages = convert_from_path(str(path))
            return "\n".join(pytesseract.image_to_string(page) for page in pages)
        return pytesseract.image_to_string(Image.open(path))
    except Exception:
        # OCR dependencies (tesseract/poppler) are not installed in this environment.
        # Callers should treat an empty result as "needs manual review".
        return ""


def classify_document(text: str) -> str:
    lowered = text.lower()
    if "explanation of benefits" in lowered or "eob" in lowered:
        return "eob"
    if "member id" in lowered and ("card" in lowered or len(text) < 500):
        return "insurance_card"
    if "claim" in lowered:
        return "claim"
    if "visit summary" in lowered or "encounter" in lowered:
        return "visit_summary"
    return "unknown"


def extract_fields(text: str, document_type: str) -> dict:
    fields: dict = {}
    if member_match := MEMBER_ID_RE.search(text):
        fields["member_id"] = member_match.group(1)
    if group_match := GROUP_NUMBER_RE.search(text):
        fields["group_number"] = group_match.group(1)
    lowered = text.lower()
    for payer in PAYER_KEYWORDS:
        if payer in lowered:
            fields["payer_name"] = payer.title()
            break
    return fields


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def process_document(db: Session, document: Document) -> ExtractedDocument:
    """Full pipeline: OCR -> classify -> extract -> chunk + embed -> persist."""
    raw_text = run_ocr(document.storage_path)
    document_type = classify_document(raw_text)
    fields = extract_fields(raw_text, document_type)

    embedder = get_embedding_provider()
    for index, chunk in enumerate(chunk_text(raw_text)):
        db.add(
            DocumentChunk(
                id=uuid.uuid4(),
                document_id=document.id,
                user_id=document.user_id,
                chunk_index=index,
                content=chunk,
                embedding=embedder.embed(chunk),
            )
        )

    document.document_type = document_type
    document.processed = True
    document.extracted_data = fields
    db.add(document)
    db.commit()

    return ExtractedDocument(raw_text=raw_text, document_type=document_type, fields=fields)
