from __future__ import annotations

import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.db import engine

router = APIRouter()

# Carpeta donde se guardan archivos (local)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # backend/app
STORAGE_ROOT = os.path.join(os.path.dirname(BASE_DIR), "storage", "ai_knowledge")  # backend/storage/ai_knowledge
os.makedirs(STORAGE_ROOT, exist_ok=True)


# =========================================================
# DB schema (auto-ensure)
# =========================================================

def ensure_knowledge_schema() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_knowledge_files (
                id TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                storage_path TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_knowledge_chunks (
                id SERIAL PRIMARY KEY,
                file_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL DEFAULT 0,
                content TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                FOREIGN KEY (file_id) REFERENCES ai_knowledge_files(id) ON DELETE CASCADE
            )
        """))


# =========================================================
# Helpers
# =========================================================

def _safe_filename(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    return name[:140] or "upload.bin"


def _detect_kind(mime: str) -> str:
    m = (mime or "").lower()
    if m.startswith("application/pdf"):
        return "pdf"
    if m.startswith("image/"):
        return "image"
    return "other"


def _save_bytes(path: str, content: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception:
        raise HTTPException(status_code=500, detail="Missing dependency: pypdf. Install with: pip install pypdf")

    import io
    reader = PdfReader(io.BytesIO(pdf_bytes))
    texts: List[str] = []
    for page in reader.pages:
        t = page.extract_text() or ""
        if t.strip():
            texts.append(t)
    return "\n\n".join(texts).strip()


def _chunk_text(text: str, max_chars: int = 1200, overlap: int = 120) -> List[str]:
    """
    Chunking simple por caracteres para Fase 1.5.
    Luego lo mejoramos con embeddings + búsqueda semántica.
    """
    t = (text or "").strip()
    if not t:
        return []

    chunks: List[str] = []
    i = 0
    n = len(t)
    while i < n:
        end = min(n, i + max_chars)
        chunk = t[i:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        i = max(0, end - overlap)
    return chunks


def _reindex_file(file_id: str) -> Dict[str, Any]:
    """
    Reextrae texto (si PDF) y rehace chunks.
    Para imágenes en esta fase: no hace visión todavía.
    """
    with engine.begin() as conn:
        f = conn.execute(text("""
            SELECT id, mime_type, storage_path
            FROM ai_knowledge_files
            WHERE id = :id
        """), {"id": file_id}).mappings().first()

        if not f:
            raise HTTPException(status_code=404, detail="file not found")

        mime = f["mime_type"]
        path = f["storage_path"]

        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="stored file not found on disk")

        # limpiar chunks previos
        conn.execute(text("DELETE FROM ai_knowledge_chunks WHERE file_id = :id"), {"id": file_id})

        kind = _detect_kind(mime)
        if kind == "pdf":
            with open(path, "rb") as fp:
                pdf_bytes = fp.read()
            full_text = _extract_pdf_text(pdf_bytes)
            chunks = _chunk_text(full_text)
            for idx, ch in enumerate(chunks):
                conn.execute(text("""
                    INSERT INTO ai_knowledge_chunks (file_id, chunk_index, content)
                    VALUES (:file_id, :chunk_index, :content)
                """), {"file_id": file_id, "chunk_index": idx, "content": ch})

            conn.execute(text("UPDATE ai_knowledge_files SET updated_at = NOW() WHERE id = :id"), {"id": file_id})
            return {"ok": True, "file_id": file_id, "chunks": len(chunks), "kind": "pdf"}

        if kind == "image":
            conn.execute(text("UPDATE ai_knowledge_files SET updated_at = NOW() WHERE id = :id"), {"id": file_id})
            return {"ok": True, "file_id": file_id, "chunks": 0, "kind": "image", "note": "vision indexing not implemented yet"}

        conn.execute(text("UPDATE ai_knowledge_files SET updated_at = NOW() WHERE id = :id"), {"id": file_id})
        return {"ok": True, "file_id": file_id, "chunks": 0, "kind": "other"}


# =========================================================
# Schemas
# =========================================================

class KnowledgeFileOut(BaseModel):
    id: str
    file_name: str
    mime_type: str
    size_bytes: int
    notes: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# =========================================================
# Routes
# NOTA: este router se monta en app/ai/router.py con prefix="/knowledge"
# Así que aquí NO repetimos "/knowledge" en las rutas.
# =========================================================

@router.post("/upload", response_model=KnowledgeFileOut)
async def upload_knowledge_file(
    file: UploadFile = File(...),
    notes: str = Form(""),
):
    ensure_knowledge_schema()

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="empty file")

    mime = (file.content_type or "application/octet-stream").split(";")[0].strip().lower()
    fname = _safe_filename(file.filename or "upload.bin")

    file_id = str(uuid.uuid4())
    storage_path = os.path.join(STORAGE_ROOT, f"{file_id}__{fname}")

    _save_bytes(storage_path, content)

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO ai_knowledge_files (
                id, file_name, mime_type, size_bytes, storage_path, notes, is_active, created_at, updated_at
            )
            VALUES (
                :id, :file_name, :mime_type, :size_bytes, :storage_path, :notes, TRUE, NOW(), NOW()
            )
        """), {
            "id": file_id,
            "file_name": fname,
            "mime_type": mime,
            "size_bytes": int(len(content)),
            "storage_path": storage_path,
            "notes": (notes or "").strip(),
        })

    # auto-index solo PDFs
    kind = _detect_kind(mime)
    if kind == "pdf":
        _reindex_file(file_id)

    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT id, file_name, mime_type, size_bytes, notes, is_active, created_at, updated_at
            FROM ai_knowledge_files
            WHERE id = :id
        """), {"id": file_id}).mappings().first()

    return KnowledgeFileOut(**dict(row))


@router.get("/files", response_model=List[KnowledgeFileOut])
def list_knowledge_files(
    active: str = Query("all", description="all|yes|no"),
    limit: int = Query(200, ge=1, le=2000),
):
    ensure_knowledge_schema()

    active = (active or "all").strip().lower()
    where = ""
    params: Dict[str, Any] = {"limit": limit}

    if active == "yes":
        where = "WHERE is_active = TRUE"
    elif active == "no":
        where = "WHERE is_active = FALSE"

    with engine.begin() as conn:
        rows = conn.execute(text(f"""
            SELECT id, file_name, mime_type, size_bytes, notes, is_active, created_at, updated_at
            FROM ai_knowledge_files
            {where}
            ORDER BY created_at DESC
            LIMIT :limit
        """), params).mappings().all()

    return [KnowledgeFileOut(**dict(r)) for r in rows]


@router.delete("/files/{file_id}")
def delete_knowledge_file(file_id: str):
    ensure_knowledge_schema()

    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT id, storage_path
            FROM ai_knowledge_files
            WHERE id = :id
        """), {"id": file_id}).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail="file not found")

        storage_path = row["storage_path"]

        # eliminar db (chunks por FK cascade)
        conn.execute(text("DELETE FROM ai_knowledge_files WHERE id = :id"), {"id": file_id})

    # eliminar archivo disco (best effort)
    try:
        if storage_path and os.path.exists(storage_path):
            os.remove(storage_path)
    except Exception:
        pass

    return {"ok": True, "deleted": file_id}


@router.post("/reindex/{file_id}")
def reindex_knowledge_file(file_id: str):
    ensure_knowledge_schema()
    return _reindex_file(file_id)
