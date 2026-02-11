import os
import re
from datetime import datetime
from typing import Optional

import requests
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text

# ✅ Router externo WhatsApp
from app.routes.whatsapp import router as whatsapp_router

# =========================================================
# APP
# =========================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(whatsapp_router)

# =========================================================
# DATABASE
# =========================================================

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

LAST_PRODUCT_CACHE: dict[str, dict] = {}

def ensure_schema():
    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversations (
                phone TEXT PRIMARY KEY,
                takeover BOOLEAN NOT NULL DEFAULT FALSE,
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                first_name TEXT,
                last_name TEXT,
                city TEXT,
                customer_type TEXT,
                interests TEXT,
                tags TEXT,
                notes TEXT
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                phone TEXT NOT NULL,
                direction TEXT NOT NULL,
                msg_type TEXT NOT NULL DEFAULT 'text',
                text TEXT NOT NULL DEFAULT '',
                media_url TEXT,
                media_caption TEXT,
                featured_image TEXT,
                real_image TEXT,
                permalink TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))

ensure_schema()

# =========================================================
# MODELS
# =========================================================

class IngestMessage(BaseModel):
    phone: str
    direction: str
    text: str

class BotReplyIn(BaseModel):
    phone: str
    text: str

class CRMIn(BaseModel):
    phone: str
    first_name: str = ""
    last_name: str = ""
    city: str = ""
    customer_type: str = ""
    interests: str = ""
    tags: str = ""
    notes: str = ""

class TakeoverPayload(BaseModel):
    phone: str
    takeover: bool

# =========================================================
# HELPERS
# =========================================================

def save_message(
    conn,
    phone: str,
    direction: str,
    text_msg: str = "",
    msg_type: str = "text",
    featured_image: Optional[str] = None,
    real_image: Optional[str] = None,
    permalink: Optional[str] = None,
):
    conn.execute(text("""
        INSERT INTO messages (
            phone, direction, msg_type, text,
            featured_image, real_image, permalink, created_at
        )
        VALUES (
            :phone, :direction, :msg_type, :text,
            :featured_image, :real_image, :permalink, :created_at
        )
    """), {
        "phone": phone,
        "direction": direction,
        "msg_type": msg_type,
        "text": text_msg,
        "featured_image": featured_image,
        "real_image": real_image,
        "permalink": permalink,
        "created_at": datetime.utcnow(),
    })

    conn.execute(text("""
        INSERT INTO conversations (phone, updated_at)
        VALUES (:phone, :updated_at)
        ON CONFLICT (phone) DO UPDATE SET updated_at = EXCLUDED.updated_at
    """), {
        "phone": phone,
        "updated_at": datetime.utcnow()
    })

# =========================================================
# ENDPOINTS
# =========================================================

@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/conversations")
def get_conversations():
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT phone, takeover, updated_at
            FROM conversations
            ORDER BY updated_at DESC
            LIMIT 200
        """)).mappings().all()
    return {"conversations": [dict(r) for r in rows]}

@app.get("/api/conversations/{phone}/messages")
def get_messages(phone: str):
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT id, phone, direction, msg_type, text,
                   featured_image, real_image, permalink, created_at
            FROM messages
            WHERE phone = :phone
            ORDER BY created_at ASC
            LIMIT 500
        """), {"phone": phone}).mappings().all()
    return {"messages": [dict(r) for r in rows]}

@app.post("/api/messages/ingest")
def ingest(msg: IngestMessage):
    with engine.begin() as conn:
        save_message(conn, msg.phone, msg.direction, msg.text)
    return {"saved": True}

@app.post("/api/conversations/takeover")
def set_takeover(payload: TakeoverPayload):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO conversations (phone, takeover, updated_at)
            VALUES (:phone, :takeover, :updated_at)
            ON CONFLICT (phone)
            DO UPDATE SET takeover = EXCLUDED.takeover,
                          updated_at = EXCLUDED.updated_at
        """), {
            "phone": payload.phone,
            "takeover": payload.takeover,
            "updated_at": datetime.utcnow()
        })
    return {"ok": True}

@app.post("/api/crm")
def save_crm(payload: CRMIn):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO conversations (
                phone, updated_at, first_name, last_name,
                city, customer_type, interests, tags, notes
            )
            VALUES (
                :phone, :updated_at, :first_name, :last_name,
                :city, :customer_type, :interests, :tags, :notes
            )
            ON CONFLICT (phone) DO UPDATE SET
              updated_at = EXCLUDED.updated_at,
              first_name = EXCLUDED.first_name,
              last_name = EXCLUDED.last_name,
              city = EXCLUDED.city,
              customer_type = EXCLUDED.customer_type,
              interests = EXCLUDED.interests,
              tags = EXCLUDED.tags,
              notes = EXCLUDED.notes
        """), {
            "phone": payload.phone,
            "updated_at": datetime.utcnow(),
            "first_name": payload.first_name,
            "last_name": payload.last_name,
            "city": payload.city,
            "customer_type": payload.customer_type,
            "interests": payload.interests,
            "tags": payload.tags,
            "notes": payload.notes,
        })
    return {"ok": True}

@app.get("/api/crm/{phone}")
def get_crm(phone: str):
    with engine.begin() as conn:
        r = conn.execute(text("""
            SELECT phone, first_name, last_name, city,
                   customer_type, interests, tags, notes
            FROM conversations
            WHERE phone = :phone
        """), {"phone": phone}).mappings().first()
    return dict(r) if r else {"phone": phone}

@app.post("/api/messages/send")
def send_message(phone: str = Query(...), text_msg: str = Query(...)):
    with engine.begin() as conn:
        save_message(conn, phone, "out", text_msg)
    return {"ok": True}
