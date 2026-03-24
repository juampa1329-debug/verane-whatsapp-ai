from __future__ import annotations

import asyncio
import html
import os
import re
import urllib.parse
import urllib.request
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
WEB_STORAGE_ROOT = os.path.join(STORAGE_ROOT, "web_sources")
os.makedirs(STORAGE_ROOT, exist_ok=True)
os.makedirs(WEB_STORAGE_ROOT, exist_ok=True)


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

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_knowledge_web_sources (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL UNIQUE,
                source_name TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                auto_sync BOOLEAN NOT NULL DEFAULT TRUE,
                sync_interval_min INTEGER NOT NULL DEFAULT 360,
                timeout_sec INTEGER NOT NULL DEFAULT 20,
                file_id TEXT NOT NULL UNIQUE,
                last_synced_at TIMESTAMP NULL,
                last_status TEXT NOT NULL DEFAULT 'never',
                last_error TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""ALTER TABLE ai_knowledge_web_sources ADD COLUMN IF NOT EXISTS source_name TEXT NOT NULL DEFAULT ''"""))
        conn.execute(text("""ALTER TABLE ai_knowledge_web_sources ADD COLUMN IF NOT EXISTS notes TEXT NOT NULL DEFAULT ''"""))
        conn.execute(text("""ALTER TABLE ai_knowledge_web_sources ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE"""))
        conn.execute(text("""ALTER TABLE ai_knowledge_web_sources ADD COLUMN IF NOT EXISTS auto_sync BOOLEAN NOT NULL DEFAULT TRUE"""))
        conn.execute(text("""ALTER TABLE ai_knowledge_web_sources ADD COLUMN IF NOT EXISTS sync_interval_min INTEGER NOT NULL DEFAULT 360"""))
        conn.execute(text("""ALTER TABLE ai_knowledge_web_sources ADD COLUMN IF NOT EXISTS timeout_sec INTEGER NOT NULL DEFAULT 20"""))
        conn.execute(text("""ALTER TABLE ai_knowledge_web_sources ADD COLUMN IF NOT EXISTS file_id TEXT NOT NULL DEFAULT ''"""))
        conn.execute(text("""ALTER TABLE ai_knowledge_web_sources ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMP NULL"""))
        conn.execute(text("""ALTER TABLE ai_knowledge_web_sources ADD COLUMN IF NOT EXISTS last_status TEXT NOT NULL DEFAULT 'never'"""))
        conn.execute(text("""ALTER TABLE ai_knowledge_web_sources ADD COLUMN IF NOT EXISTS last_error TEXT NOT NULL DEFAULT ''"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_ai_kb_ws_active_auto ON ai_knowledge_web_sources (is_active, auto_sync)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_ai_kb_ws_last_synced ON ai_knowledge_web_sources (last_synced_at)"""))


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
    if m.startswith("text/") or m in {"application/json", "application/xml", "text/xml"}:
        return "text"
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


def _replace_chunks(conn, file_id: str, chunks: List[str]) -> None:
    conn.execute(text("DELETE FROM ai_knowledge_chunks WHERE file_id = :id"), {"id": file_id})
    for idx, ch in enumerate(chunks):
        conn.execute(text("""
            INSERT INTO ai_knowledge_chunks (file_id, chunk_index, content)
            VALUES (:file_id, :chunk_index, :content)
        """), {"file_id": file_id, "chunk_index": idx, "content": ch})


def _normalize_web_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="url is required")
    if not re.match(r"^https?://", raw, flags=re.IGNORECASE):
        raw = f"https://{raw}"
    p = urllib.parse.urlparse(raw)
    if p.scheme not in {"http", "https"} or not p.netloc:
        raise HTTPException(status_code=400, detail="url must be http/https")
    p = p._replace(fragment="")
    return urllib.parse.urlunparse(p)


def _html_to_text(doc: str) -> str:
    t = doc or ""
    t = re.sub(r"(?is)<(script|style|noscript|svg).*?>.*?</\1>", " ", t)
    t = re.sub(r"(?is)<br\s*/?>", "\n", t)
    t = re.sub(r"(?is)</(p|div|li|h1|h2|h3|h4|h5|h6|section|article|tr)>", "\n", t)
    t = re.sub(r"(?is)<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _fetch_web_text(url: str, timeout_sec: int = 20, max_bytes: int = 2_000_000) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "VeraneAI-KB/1.0 (+https://app.perfumesverane.com)",
            "Accept": "text/html, text/plain, application/xhtml+xml;q=0.9, */*;q=0.5",
        },
    )
    with urllib.request.urlopen(req, timeout=int(max(5, min(timeout_sec, 60)))) as resp:
        content_type = str(resp.headers.get("Content-Type") or "").lower()
        charset = resp.headers.get_content_charset() or "utf-8"
        raw = resp.read(int(max(20_000, min(max_bytes, 5_000_000))))

    try:
        decoded = raw.decode(charset, errors="ignore")
    except Exception:
        decoded = raw.decode("utf-8", errors="ignore")

    looks_html = ("html" in content_type) or ("<html" in decoded[:800].lower())
    if looks_html:
        txt = _html_to_text(decoded)
    else:
        txt = html.unescape(decoded).strip()

    txt = re.sub(r"\s+\n", "\n", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt).strip()
    if not txt:
        raise HTTPException(status_code=422, detail="No text extracted from URL")
    return txt


def _sync_web_source_now(source_id: str, *, raise_http: bool = True) -> Dict[str, Any]:
    ensure_knowledge_schema()
    sid = (source_id or "").strip()
    if not sid:
        raise HTTPException(status_code=400, detail="source_id is required")

    with engine.begin() as conn:
        src = conn.execute(text("""
            SELECT
                id, url, source_name, notes, is_active, auto_sync,
                sync_interval_min, timeout_sec, file_id
            FROM ai_knowledge_web_sources
            WHERE id = :id
        """), {"id": sid}).mappings().first()

    if not src:
        raise HTTPException(status_code=404, detail="web source not found")

    srcd = dict(src)
    url = _normalize_web_url(str(srcd.get("url") or ""))
    timeout_sec = int(max(5, min(int(srcd.get("timeout_sec") or 20), 60)))
    file_id = str(srcd.get("file_id") or "").strip()
    if not file_id:
        raise HTTPException(status_code=500, detail="web source missing file_id")

    try:
        content_text = _fetch_web_text(url=url, timeout_sec=timeout_sec)
        chunks = _chunk_text(content_text)

        storage_path = os.path.join(WEB_STORAGE_ROOT, f"{sid}.txt")
        with open(storage_path, "w", encoding="utf-8") as fp:
            fp.write(content_text)

        size_bytes = int(os.path.getsize(storage_path))
        file_name = (srcd.get("source_name") or url)[:180]
        notes = (srcd.get("notes") or "").strip()
        file_notes = f"[web] {url}" + (f" | {notes}" if notes else "")

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO ai_knowledge_files (
                    id, file_name, mime_type, size_bytes, storage_path, notes, is_active, created_at, updated_at
                )
                VALUES (
                    :id, :file_name, 'text/plain', :size_bytes, :storage_path, :notes, :is_active, NOW(), NOW()
                )
                ON CONFLICT (id) DO UPDATE SET
                    file_name = EXCLUDED.file_name,
                    mime_type = EXCLUDED.mime_type,
                    size_bytes = EXCLUDED.size_bytes,
                    storage_path = EXCLUDED.storage_path,
                    notes = EXCLUDED.notes,
                    is_active = EXCLUDED.is_active,
                    updated_at = NOW()
            """), {
                "id": file_id,
                "file_name": file_name,
                "size_bytes": size_bytes,
                "storage_path": storage_path,
                "notes": file_notes,
                "is_active": bool(srcd.get("is_active", True)),
            })

            _replace_chunks(conn, file_id=file_id, chunks=chunks)
            conn.execute(text("""
                UPDATE ai_knowledge_web_sources
                SET
                    last_synced_at = NOW(),
                    last_status = 'ok',
                    last_error = '',
                    updated_at = NOW()
                WHERE id = :id
            """), {"id": sid})

        return {
            "ok": True,
            "source_id": sid,
            "file_id": file_id,
            "url": url,
            "chunks": len(chunks),
            "size_bytes": size_bytes,
        }
    except HTTPException as he:
        err = str(he.detail)[:700]
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE ai_knowledge_web_sources
                SET last_status = 'error', last_error = :err, updated_at = NOW()
                WHERE id = :id
            """), {"id": sid, "err": err})
        if raise_http:
            raise
        return {"ok": False, "source_id": sid, "error": err}
    except Exception as e:
        err = str(e)[:700]
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE ai_knowledge_web_sources
                SET last_status = 'error', last_error = :err, updated_at = NOW()
                WHERE id = :id
            """), {"id": sid, "err": err})
        if raise_http:
            raise HTTPException(status_code=502, detail=f"web sync failed: {err}")
        return {"ok": False, "source_id": sid, "error": err}


def _is_source_due(row: Dict[str, Any], now: datetime) -> bool:
    if not bool(row.get("is_active")) or not bool(row.get("auto_sync")):
        return False
    interval_min = int(max(5, min(int(row.get("sync_interval_min") or 360), 10080)))
    last_sync = row.get("last_synced_at")
    if not isinstance(last_sync, datetime):
        return True
    return (now - last_sync).total_seconds() >= (interval_min * 60)


async def sync_due_web_sources(limit: int = 10) -> Dict[str, Any]:
    ensure_knowledge_schema()
    lim = int(max(1, min(limit, 100)))

    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT
                id, is_active, auto_sync, sync_interval_min, last_synced_at
            FROM ai_knowledge_web_sources
            WHERE is_active = TRUE AND auto_sync = TRUE
            ORDER BY CASE WHEN last_synced_at IS NULL THEN 0 ELSE 1 END ASC, last_synced_at ASC, created_at ASC
            LIMIT 500
        """)).mappings().all()

    now = datetime.utcnow()
    due_ids: List[str] = []
    for r in rows:
        d = dict(r)
        if _is_source_due(d, now):
            due_ids.append(str(d.get("id")))
        if len(due_ids) >= lim:
            break

    done = 0
    failed = 0
    details: List[Dict[str, Any]] = []
    for sid in due_ids:
        res = await asyncio.to_thread(_sync_web_source_now, sid, raise_http=False)
        details.append(res)
        if res.get("ok"):
            done += 1
        else:
            failed += 1

    return {
        "ok": True,
        "checked": len(rows),
        "due": len(due_ids),
        "synced": done,
        "failed": failed,
        "results": details,
    }


async def start_web_sources_sync_loop(interval_sec: int = 180) -> None:
    """
    Loop de auto-sync de fuentes web de KB.
    """
    wait_sec = int(max(30, min(interval_sec, 3600)))
    while True:
        try:
            await sync_due_web_sources(limit=20)
        except Exception:
            pass
        await asyncio.sleep(wait_sec)


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

        kind = _detect_kind(mime)
        if kind == "pdf":
            with open(path, "rb") as fp:
                pdf_bytes = fp.read()
            full_text = _extract_pdf_text(pdf_bytes)
            chunks = _chunk_text(full_text)
            _replace_chunks(conn, file_id=file_id, chunks=chunks)

            conn.execute(text("UPDATE ai_knowledge_files SET updated_at = NOW() WHERE id = :id"), {"id": file_id})
            return {"ok": True, "file_id": file_id, "chunks": len(chunks), "kind": "pdf"}

        if kind == "text":
            with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                full_text = fp.read()
            chunks = _chunk_text(full_text)
            _replace_chunks(conn, file_id=file_id, chunks=chunks)
            conn.execute(text("UPDATE ai_knowledge_files SET updated_at = NOW() WHERE id = :id"), {"id": file_id})
            return {"ok": True, "file_id": file_id, "chunks": len(chunks), "kind": "text"}

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


class KnowledgeWebSourceIn(BaseModel):
    url: str
    source_name: str = ""
    notes: str = ""
    is_active: bool = True
    auto_sync: bool = True
    sync_interval_min: int = 360
    timeout_sec: int = 20


class KnowledgeWebSourcePatch(BaseModel):
    url: Optional[str] = None
    source_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    auto_sync: Optional[bool] = None
    sync_interval_min: Optional[int] = None
    timeout_sec: Optional[int] = None


class KnowledgeWebSourceOut(BaseModel):
    id: str
    url: str
    source_name: str = ""
    notes: str = ""
    is_active: bool = True
    auto_sync: bool = True
    sync_interval_min: int = 360
    timeout_sec: int = 20
    file_id: str
    last_synced_at: Optional[datetime] = None
    last_status: str = "never"
    last_error: str = ""
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

    # auto-index para PDF/text
    kind = _detect_kind(mime)
    if kind in {"pdf", "text"}:
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


@router.get("/web-sources", response_model=List[KnowledgeWebSourceOut])
def list_web_sources(
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
            SELECT
                id, url, source_name, notes, is_active, auto_sync, sync_interval_min, timeout_sec,
                file_id, last_synced_at, last_status, last_error, created_at, updated_at
            FROM ai_knowledge_web_sources
            {where}
            ORDER BY created_at DESC
            LIMIT :limit
        """), params).mappings().all()
    return [KnowledgeWebSourceOut(**dict(r)) for r in rows]


@router.post("/web-sources", response_model=KnowledgeWebSourceOut)
def create_web_source(payload: KnowledgeWebSourceIn):
    ensure_knowledge_schema()
    source_id = str(uuid.uuid4())
    file_id = f"websrc::{source_id}"
    url = _normalize_web_url(payload.url)
    source_name = (payload.source_name or "").strip()
    notes = (payload.notes or "").strip()
    sync_interval_min = int(max(5, min(int(payload.sync_interval_min or 360), 10080)))
    timeout_sec = int(max(5, min(int(payload.timeout_sec or 20), 60)))

    with engine.begin() as conn:
        try:
            conn.execute(text("""
                INSERT INTO ai_knowledge_web_sources (
                    id, url, source_name, notes, is_active, auto_sync, sync_interval_min,
                    timeout_sec, file_id, last_status, last_error, created_at, updated_at
                )
                VALUES (
                    :id, :url, :source_name, :notes, :is_active, :auto_sync, :sync_interval_min,
                    :timeout_sec, :file_id, 'never', '', NOW(), NOW()
                )
            """), {
                "id": source_id,
                "url": url,
                "source_name": source_name,
                "notes": notes,
                "is_active": bool(payload.is_active),
                "auto_sync": bool(payload.auto_sync),
                "sync_interval_min": sync_interval_min,
                "timeout_sec": timeout_sec,
                "file_id": file_id,
            })
        except Exception as e:
            msg = str(e).lower()
            if "unique" in msg and "url" in msg:
                raise HTTPException(status_code=409, detail="URL already exists")
            raise

        row = conn.execute(text("""
            SELECT
                id, url, source_name, notes, is_active, auto_sync, sync_interval_min, timeout_sec,
                file_id, last_synced_at, last_status, last_error, created_at, updated_at
            FROM ai_knowledge_web_sources
            WHERE id = :id
        """), {"id": source_id}).mappings().first()
    return KnowledgeWebSourceOut(**dict(row))


@router.put("/web-sources/{source_id}", response_model=KnowledgeWebSourceOut)
def update_web_source(source_id: str, payload: KnowledgeWebSourcePatch):
    ensure_knowledge_schema()
    sid = (source_id or "").strip()
    if not sid:
        raise HTTPException(status_code=400, detail="source_id is required")

    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT
                id, url, source_name, notes, is_active, auto_sync, sync_interval_min, timeout_sec,
                file_id, last_synced_at, last_status, last_error, created_at, updated_at
            FROM ai_knowledge_web_sources
            WHERE id = :id
        """), {"id": sid}).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="web source not found")

        current = dict(row)
        next_url = _normalize_web_url(payload.url) if payload.url is not None else str(current.get("url") or "")
        next_source_name = str(current.get("source_name") or "") if payload.source_name is None else str(payload.source_name or "").strip()
        next_notes = str(current.get("notes") or "") if payload.notes is None else str(payload.notes or "").strip()
        next_active = bool(current.get("is_active")) if payload.is_active is None else bool(payload.is_active)
        next_auto = bool(current.get("auto_sync")) if payload.auto_sync is None else bool(payload.auto_sync)
        next_interval = int(current.get("sync_interval_min") or 360) if payload.sync_interval_min is None else int(payload.sync_interval_min)
        next_timeout = int(current.get("timeout_sec") or 20) if payload.timeout_sec is None else int(payload.timeout_sec)
        next_interval = int(max(5, min(next_interval, 10080)))
        next_timeout = int(max(5, min(next_timeout, 60)))

        try:
            conn.execute(text("""
                UPDATE ai_knowledge_web_sources
                SET
                    url = :url,
                    source_name = :source_name,
                    notes = :notes,
                    is_active = :is_active,
                    auto_sync = :auto_sync,
                    sync_interval_min = :sync_interval_min,
                    timeout_sec = :timeout_sec,
                    updated_at = NOW()
                WHERE id = :id
            """), {
                "id": sid,
                "url": next_url,
                "source_name": next_source_name,
                "notes": next_notes,
                "is_active": next_active,
                "auto_sync": next_auto,
                "sync_interval_min": next_interval,
                "timeout_sec": next_timeout,
            })
        except Exception as e:
            msg = str(e).lower()
            if "unique" in msg and "url" in msg:
                raise HTTPException(status_code=409, detail="URL already exists")
            raise

        if not next_active:
            conn.execute(text("""
                UPDATE ai_knowledge_files
                SET is_active = FALSE, updated_at = NOW()
                WHERE id = :file_id
            """), {"file_id": str(current.get("file_id") or "")})

        out = conn.execute(text("""
            SELECT
                id, url, source_name, notes, is_active, auto_sync, sync_interval_min, timeout_sec,
                file_id, last_synced_at, last_status, last_error, created_at, updated_at
            FROM ai_knowledge_web_sources
            WHERE id = :id
        """), {"id": sid}).mappings().first()

    return KnowledgeWebSourceOut(**dict(out))


@router.delete("/web-sources/{source_id}")
def delete_web_source(source_id: str):
    ensure_knowledge_schema()
    sid = (source_id or "").strip()
    if not sid:
        raise HTTPException(status_code=400, detail="source_id is required")

    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT id, file_id
            FROM ai_knowledge_web_sources
            WHERE id = :id
        """), {"id": sid}).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="web source not found")

        file_id = str(row.get("file_id") or "")
        path_row = conn.execute(text("""
            SELECT storage_path FROM ai_knowledge_files WHERE id = :id
        """), {"id": file_id}).mappings().first()
        storage_path = str((path_row or {}).get("storage_path") or "")

        conn.execute(text("DELETE FROM ai_knowledge_web_sources WHERE id = :id"), {"id": sid})
        conn.execute(text("DELETE FROM ai_knowledge_files WHERE id = :id"), {"id": file_id})

    try:
        if storage_path and os.path.exists(storage_path):
            os.remove(storage_path)
    except Exception:
        pass

    return {"ok": True, "deleted": sid}


@router.post("/web-sources/{source_id}/sync")
async def sync_web_source(source_id: str):
    res = await asyncio.to_thread(_sync_web_source_now, source_id, raise_http=True)
    return res


@router.post("/web-sources/sync-due")
async def sync_due_sources(limit: int = Query(10, ge=1, le=100)):
    return await sync_due_web_sources(limit=limit)
