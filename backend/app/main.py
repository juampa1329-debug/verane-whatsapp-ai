# app/main.py

import asyncio
import base64
import hashlib
import json
import os
import re
import secrets
import time
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from starlette.requests import Request as StarletteRequest

from app.db import engine
from app.campaigns.engine import campaign_engine_tick, engine_settings, run_campaign_engine_forever
from app.automation.trigger_engine import get_trigger_catalog
from app.remarketing.engine import (
    process_due_remarketing,
    remarketing_settings,
    list_stage_catalog,
    get_phone_enrollments,
    assign_phone_stage,
)
from app.catalog.sync_service import (
    start_periodic_sync,
    get_sync_state as get_wc_sync_state,
    sync_all_products_once,
    sync_recent_products_once,
)
from app.ai.knowledge_router import start_web_sources_sync_loop
from app.catalog.cache_repo import get_cache_stats

# ✅ Pipeline core (nuevo flujo real)
from app.pipeline.ingest_core import run_ingest, IngestMessage
from app.ai.context_builder import build_ai_meta
from app.ai.intent_router import detect_intent

# ✅ Woo sender (endpoint manual)
from app.pipeline.wc_sender import wc_send_product

# ✅ Router WhatsApp (webhook)
from app.routes.whatsapp import (
    router as whatsapp_router,
    upload_whatsapp_media,
)
from app.routes.social import router as social_router

# ✅ Woo utils (búsqueda UI)
from app.integrations.woocommerce import (
    wc_get,
    map_product_for_ui,
    wc_enabled,
)

# ✅ Montar router IA (si existe)
try:
    from app.ai.router import router as ai_router
except Exception:
    ai_router = None


# =========================================================
# APP
# =========================================================

app = FastAPI()
_campaign_engine_stop: Optional[asyncio.Event] = None
_campaign_engine_task: Optional[asyncio.Task] = None
_remarketing_engine_stop: Optional[asyncio.Event] = None
_remarketing_engine_task: Optional[asyncio.Task] = None
_wc_cache_sync_task: Optional[asyncio.Task] = None
_kb_web_sync_task: Optional[asyncio.Task] = None
_security_key_rotation_stop: Optional[asyncio.Event] = None
_security_key_rotation_task: Optional[asyncio.Task] = None
_firebase_admin_app = None

origins = [
    "https://app.perfumesverane.com",
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https://.*\.perfumesverane\.com$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(whatsapp_router)
app.include_router(social_router)
if ai_router is not None:
    app.include_router(ai_router, prefix="/api/ai")

# Webhooks Woo
from app.routes.wc_webhooks import router as wc_webhooks_router
app.include_router(wc_webhooks_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: StarletteRequest, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": str(exc),
            "path": str(request.url.path),
        },
    )


# =========================================================
# DATABASE SCHEMA
# =========================================================

def ensure_schema():
    """
    Crea/actualiza el schema mínimo que el CRM + pipeline necesita.
    (Seguro si ya existe; usa IF NOT EXISTS / ALTER ... IF NOT EXISTS)
    """
    with engine.begin() as conn:
        # -------------------------
        # conversations
        # -------------------------
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
                notes TEXT,

                last_read_at TIMESTAMP,

                ai_state TEXT,

                wc_last_options JSONB,
                wc_last_options_at TIMESTAMP
            )
        """))

        # ✅ columnas extra para memoria del último producto (best-effort)
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_product_id BIGINT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS crm_meta JSONB"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS crm_slots JSONB"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_product_featured_image TEXT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_product_real_image TEXT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_product_permalink TEXT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS intent_current TEXT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS intent_confidence DOUBLE PRECISION"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS intent_stage TEXT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS intent_product_query TEXT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS intent_product_candidates JSONB"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS intent_preferences JSONB"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS payment_status TEXT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS payment_reference TEXT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS payment_amount TEXT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS payment_currency TEXT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_reconstructed_at TIMESTAMP"""))

        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations (updated_at)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_conversations_intent_current ON conversations (intent_current)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_conversations_payment_status ON conversations (payment_status)"""))

        # -------------------------
        # messages
        # -------------------------
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                phone TEXT NOT NULL,
                channel TEXT NOT NULL DEFAULT 'whatsapp',
                direction TEXT NOT NULL,
                msg_type TEXT NOT NULL DEFAULT 'text',
                text TEXT NOT NULL DEFAULT '',

                media_url TEXT,
                media_caption TEXT,

                media_id TEXT,
                mime_type TEXT,
                file_name TEXT,
                file_size INTEGER,
                duration_sec INTEGER,

                featured_image TEXT,
                real_image TEXT,
                permalink TEXT,

                extracted_text TEXT,
                ai_meta JSONB,

                wa_message_id TEXT,
                wa_status TEXT,
                wa_error TEXT,
                wa_ts_sent TIMESTAMP,
                wa_ts_delivered TIMESTAMP,
                wa_ts_read TIMESTAMP,

                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS channel TEXT NOT NULL DEFAULT 'whatsapp'"""))

        # Índices útiles para tu UI
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_messages_phone_created_at ON messages (phone, created_at)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_messages_phone_channel_created_at ON messages (phone, channel, created_at)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_messages_channel_created_at ON messages (channel, created_at)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_messages_phone_direction_created_at ON messages (phone, direction, created_at)"""))

        # -------------------------
        # ai_settings
        # -------------------------
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_settings (
                id SERIAL PRIMARY KEY,

                is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                provider TEXT NOT NULL DEFAULT 'google',
                model TEXT NOT NULL DEFAULT 'gemini-2.5-flash',
                system_prompt TEXT NOT NULL DEFAULT '',
                max_tokens INTEGER NOT NULL DEFAULT 512,
                temperature DOUBLE PRECISION NOT NULL DEFAULT 0.7,

                fallback_provider TEXT NOT NULL DEFAULT 'groq',
                fallback_model TEXT NOT NULL DEFAULT 'llama-3.1-8b-instant',

                timeout_sec INTEGER NOT NULL DEFAULT 25,
                max_retries INTEGER NOT NULL DEFAULT 1,

                reply_chunk_chars INTEGER,
                reply_delay_ms INTEGER,
                typing_delay_ms INTEGER,
                inbound_cooldown_sec INTEGER,
                inbound_post_activity_ms INTEGER,
                inbound_audio_extra_ms INTEGER,

                voice_enabled BOOLEAN,
                voice_gender TEXT,
                voice_language TEXT,
                voice_accent TEXT,
                voice_style_prompt TEXT,
                voice_max_notes_per_reply INTEGER,
                voice_prefer_voice BOOLEAN,
                voice_speaking_rate DOUBLE PRECISION,

                voice_tts_provider TEXT,
                voice_tts_voice_id TEXT,
                voice_tts_model_id TEXT,

                mm_enabled BOOLEAN,
                mm_provider TEXT,
                mm_model TEXT,
                mm_timeout_sec INTEGER,
                mm_max_retries INTEGER,

                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS inbound_cooldown_sec INTEGER"""))
        conn.execute(text("""ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS inbound_post_activity_ms INTEGER"""))
        conn.execute(text("""ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS inbound_audio_extra_ms INTEGER"""))

        # Insertar 1 fila default si la tabla está vacía
        conn.execute(text("""
            INSERT INTO ai_settings (
                is_enabled, provider, model, system_prompt,
                max_tokens, temperature,
                fallback_provider, fallback_model,
                timeout_sec, max_retries,

                reply_chunk_chars, reply_delay_ms, typing_delay_ms,
                inbound_cooldown_sec, inbound_post_activity_ms, inbound_audio_extra_ms,

                voice_enabled, voice_prefer_voice, voice_max_notes_per_reply,
                voice_tts_provider, voice_tts_voice_id, voice_tts_model_id,

                mm_enabled, mm_provider, mm_model, mm_timeout_sec, mm_max_retries
            )
            SELECT
                TRUE, 'google', 'gemini-2.5-flash', '',
                512, 0.7,
                'groq', 'llama-3.1-8b-instant',
                25, 1,

                480, 900, 450,
                6, 1400, 2500,

                FALSE, FALSE, 1,
                'google', '', '',

                TRUE, 'google', 'gemini-2.5-flash', 75, 2
            WHERE NOT EXISTS (SELECT 1 FROM ai_settings)
        """))

        # Asegurar defaults si quedaron NULL
        conn.execute(text("""
            UPDATE ai_settings
            SET
                reply_chunk_chars = COALESCE(reply_chunk_chars, 480),
                reply_delay_ms = COALESCE(reply_delay_ms, 900),
                typing_delay_ms = COALESCE(typing_delay_ms, 450),
                inbound_cooldown_sec = COALESCE(inbound_cooldown_sec, 6),
                inbound_post_activity_ms = COALESCE(inbound_post_activity_ms, 1400),
                inbound_audio_extra_ms = COALESCE(inbound_audio_extra_ms, 2500),

                voice_enabled = COALESCE(voice_enabled, FALSE),
                voice_prefer_voice = COALESCE(voice_prefer_voice, FALSE),
                voice_max_notes_per_reply = COALESCE(voice_max_notes_per_reply, 1),

                voice_tts_provider = COALESCE(NULLIF(TRIM(voice_tts_provider), ''), 'google'),
                voice_tts_voice_id = COALESCE(NULLIF(TRIM(voice_tts_voice_id), ''), ''),
                voice_tts_model_id = COALESCE(NULLIF(TRIM(voice_tts_model_id), ''), ''),

                mm_enabled = COALESCE(mm_enabled, TRUE),
                mm_provider = COALESCE(NULLIF(TRIM(mm_provider), ''), 'google'),
                mm_model = COALESCE(NULLIF(TRIM(mm_model), ''), 'gemini-2.5-flash'),
                mm_timeout_sec = COALESCE(mm_timeout_sec, 75),
                mm_max_retries = COALESCE(mm_max_retries, 2)
            WHERE id = (SELECT id FROM ai_settings ORDER BY id ASC LIMIT 1)
        """))

        # -------------------------
        # wc_products_cache (Plan B) - V2 (cache_repo compatible)
        # -------------------------
        try:
            conn.execute(text("""CREATE EXTENSION IF NOT EXISTS pg_trgm"""))
        except Exception:
            pass

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS wc_products_cache (
                product_id BIGINT PRIMARY KEY,
                data JSONB NOT NULL DEFAULT '{}'::jsonb,

                name TEXT NOT NULL DEFAULT '',
                price TEXT NOT NULL DEFAULT '',
                permalink TEXT NOT NULL DEFAULT '',

                featured_image TEXT NOT NULL DEFAULT '',
                real_image TEXT NOT NULL DEFAULT '',
                stock_status TEXT NOT NULL DEFAULT '',

                updated_at_woo TIMESTAMP NULL,
                synced_at TIMESTAMP NOT NULL DEFAULT NOW(),

                search_blob TEXT NOT NULL DEFAULT ''
            )
        """))

        # índices
        try:
            conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_wc_cache_name_trgm ON wc_products_cache USING gin (name gin_trgm_ops)"""))
        except Exception:
            pass

        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_wc_cache_synced_at ON wc_products_cache (synced_at)"""))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS wc_sync_state (
                id INTEGER PRIMARY KEY,
                last_sync_at TIMESTAMP NULL,
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            INSERT INTO wc_sync_state (id, last_sync_at, updated_at)
            VALUES (1, NULL, NOW())
            ON CONFLICT (id) DO NOTHING
        """))

        # -------------------------
        # customer_segments
        # -------------------------
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS customer_segments (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                rules_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_customer_segments_active ON customer_segments (is_active)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_customer_segments_updated_at ON customer_segments (updated_at DESC)"""))

        # -------------------------
        # crm_labels
        # -------------------------
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS crm_labels (
                id SERIAL PRIMARY KEY,
                label_key TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                color TEXT NOT NULL DEFAULT '#64748b',
                icon TEXT NOT NULL DEFAULT 'tag',
                description TEXT NOT NULL DEFAULT '',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""ALTER TABLE crm_labels ADD COLUMN IF NOT EXISTS label_key TEXT"""))
        conn.execute(text("""ALTER TABLE crm_labels ADD COLUMN IF NOT EXISTS color TEXT NOT NULL DEFAULT '#64748b'"""))
        conn.execute(text("""ALTER TABLE crm_labels ADD COLUMN IF NOT EXISTS icon TEXT NOT NULL DEFAULT 'tag'"""))
        conn.execute(text("""ALTER TABLE crm_labels ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT ''"""))
        conn.execute(text("""ALTER TABLE crm_labels ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE"""))
        conn.execute(text("""ALTER TABLE crm_labels ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()"""))
        conn.execute(text("""ALTER TABLE crm_labels ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()"""))
        conn.execute(text("""
            UPDATE crm_labels
            SET label_key = CASE
                WHEN COALESCE(TRIM(label_key),'') <> '' THEN LOWER(TRIM(label_key))
                ELSE LOWER(REGEXP_REPLACE(COALESCE(name,''), '[^a-zA-Z0-9]+', '_', 'g'))
            END
        """))
        conn.execute(text("""
            UPDATE crm_labels
            SET label_key = CONCAT('label_', id)
            WHERE COALESCE(TRIM(label_key),'') = ''
        """))
        conn.execute(text("""
            WITH dups AS (
                SELECT id, label_key, ROW_NUMBER() OVER (PARTITION BY label_key ORDER BY id ASC) AS rn
                FROM crm_labels
            )
            UPDATE crm_labels l
            SET label_key = CONCAT(l.label_key, '_', l.id)
            FROM dups
            WHERE dups.id = l.id
              AND dups.rn > 1
        """))
        conn.execute(text("""CREATE UNIQUE INDEX IF NOT EXISTS uq_crm_labels_label_key ON crm_labels (label_key)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_crm_labels_active ON crm_labels (is_active)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_crm_labels_updated_at ON crm_labels (updated_at DESC)"""))

        # -------------------------
        # message_templates
        # -------------------------
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS message_templates (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                channel TEXT NOT NULL DEFAULT 'whatsapp',
                body TEXT NOT NULL DEFAULT '',
                variables_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                blocks_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                params_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                render_mode TEXT NOT NULL DEFAULT 'chat',
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""ALTER TABLE message_templates ADD COLUMN IF NOT EXISTS channel TEXT NOT NULL DEFAULT 'whatsapp'"""))
        conn.execute(text("""ALTER TABLE message_templates ADD COLUMN IF NOT EXISTS blocks_json JSONB NOT NULL DEFAULT '[]'::jsonb"""))
        conn.execute(text("""ALTER TABLE message_templates ADD COLUMN IF NOT EXISTS params_json JSONB NOT NULL DEFAULT '{}'::jsonb"""))
        conn.execute(text("""ALTER TABLE message_templates ADD COLUMN IF NOT EXISTS render_mode TEXT NOT NULL DEFAULT 'chat'"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_message_templates_channel ON message_templates (channel)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_message_templates_status ON message_templates (status)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_message_templates_updated_at ON message_templates (updated_at DESC)"""))

        # -------------------------
        # campaigns
        # -------------------------
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                objective TEXT NOT NULL DEFAULT '',
                segment_id INTEGER REFERENCES customer_segments(id) ON DELETE SET NULL,
                template_id INTEGER REFERENCES message_templates(id) ON DELETE SET NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                scheduled_at TIMESTAMP NULL,
                launched_at TIMESTAMP NULL,
                channel TEXT NOT NULL DEFAULT 'whatsapp',
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns (status)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_campaigns_scheduled_at ON campaigns (scheduled_at)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_campaigns_updated_at ON campaigns (updated_at DESC)"""))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS campaign_recipients (
                id SERIAL PRIMARY KEY,
                campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
                phone TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                sent_at TIMESTAMP NULL,
                delivered_at TIMESTAMP NULL,
                read_at TIMESTAMP NULL,
                replied_at TIMESTAMP NULL,
                error TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE (campaign_id, phone)
            )
        """))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_campaign_recipients_campaign_id ON campaign_recipients (campaign_id)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_campaign_recipients_status ON campaign_recipients (status)"""))
        conn.execute(text("""ALTER TABLE campaign_recipients ADD COLUMN IF NOT EXISTS wa_message_id TEXT"""))
        conn.execute(text("""ALTER TABLE campaign_recipients ADD COLUMN IF NOT EXISTS message_id INTEGER"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_campaign_recipients_wa_message_id ON campaign_recipients (wa_message_id)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_campaign_recipients_message_id ON campaign_recipients (message_id)"""))

        # -------------------------
        # automation_triggers
        # -------------------------
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS automation_triggers (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                channel TEXT NOT NULL DEFAULT 'whatsapp',
                event_type TEXT NOT NULL,
                trigger_type TEXT NOT NULL DEFAULT 'message_flow',
                flow_event TEXT NOT NULL DEFAULT 'received',
                conditions_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                action_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                cooldown_minutes INTEGER NOT NULL DEFAULT 60,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                assistant_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                assistant_message_type TEXT NOT NULL DEFAULT 'auto',
                priority INTEGER NOT NULL DEFAULT 100,
                block_ai BOOLEAN NOT NULL DEFAULT TRUE,
                stop_on_match BOOLEAN NOT NULL DEFAULT TRUE,
                only_when_no_takeover BOOLEAN NOT NULL DEFAULT TRUE,
                last_run_at TIMESTAMP NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""ALTER TABLE automation_triggers ADD COLUMN IF NOT EXISTS channel TEXT NOT NULL DEFAULT 'whatsapp'"""))
        conn.execute(text("""ALTER TABLE automation_triggers ADD COLUMN IF NOT EXISTS trigger_type TEXT NOT NULL DEFAULT 'message_flow'"""))
        conn.execute(text("""ALTER TABLE automation_triggers ADD COLUMN IF NOT EXISTS flow_event TEXT NOT NULL DEFAULT 'received'"""))
        conn.execute(text("""ALTER TABLE automation_triggers ADD COLUMN IF NOT EXISTS assistant_enabled BOOLEAN NOT NULL DEFAULT FALSE"""))
        conn.execute(text("""ALTER TABLE automation_triggers ADD COLUMN IF NOT EXISTS assistant_message_type TEXT NOT NULL DEFAULT 'auto'"""))
        conn.execute(text("""ALTER TABLE automation_triggers ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 100"""))
        conn.execute(text("""ALTER TABLE automation_triggers ADD COLUMN IF NOT EXISTS block_ai BOOLEAN NOT NULL DEFAULT TRUE"""))
        conn.execute(text("""ALTER TABLE automation_triggers ADD COLUMN IF NOT EXISTS stop_on_match BOOLEAN NOT NULL DEFAULT TRUE"""))
        conn.execute(text("""ALTER TABLE automation_triggers ADD COLUMN IF NOT EXISTS only_when_no_takeover BOOLEAN NOT NULL DEFAULT TRUE"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_automation_triggers_active ON automation_triggers (is_active)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_automation_triggers_event_type ON automation_triggers (event_type)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_automation_triggers_channel ON automation_triggers (channel)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_automation_triggers_trigger_type ON automation_triggers (trigger_type)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_automation_triggers_flow_event ON automation_triggers (flow_event)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_automation_triggers_priority ON automation_triggers (priority, id)"""))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS trigger_executions (
                id SERIAL PRIMARY KEY,
                trigger_id INTEGER NOT NULL REFERENCES automation_triggers(id) ON DELETE CASCADE,
                phone TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ok',
                executed_at TIMESTAMP NOT NULL DEFAULT NOW(),
                error TEXT,
                details JSONB NOT NULL DEFAULT '{}'::jsonb
            )
        """))
        conn.execute(text("""ALTER TABLE trigger_executions ADD COLUMN IF NOT EXISTS details JSONB NOT NULL DEFAULT '{}'::jsonb"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_trigger_executions_trigger_id ON trigger_executions (trigger_id)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_trigger_executions_executed_at ON trigger_executions (executed_at DESC)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_trigger_executions_trigger_phone ON trigger_executions (trigger_id, phone, executed_at DESC)"""))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS trigger_scheduled_messages (
                id SERIAL PRIMARY KEY,
                trigger_id INTEGER REFERENCES automation_triggers(id) ON DELETE SET NULL,
                phone TEXT NOT NULL,
                template_id INTEGER REFERENCES message_templates(id) ON DELETE SET NULL,
                payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                run_at TIMESTAMP NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                sent_at TIMESTAMP NULL
            )
        """))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_trigger_scheduled_status_runat ON trigger_scheduled_messages (status, run_at)"""))

        # -------------------------
        # remarketing flows
        # -------------------------
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS remarketing_flows (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                channel TEXT NOT NULL DEFAULT 'whatsapp',
                entry_rules_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                exit_rules_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                is_active BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""ALTER TABLE remarketing_flows ADD COLUMN IF NOT EXISTS channel TEXT NOT NULL DEFAULT 'whatsapp'"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_remarketing_flows_active ON remarketing_flows (is_active)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_remarketing_flows_channel ON remarketing_flows (channel)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_remarketing_flows_updated_at ON remarketing_flows (updated_at DESC)"""))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS remarketing_steps (
                id SERIAL PRIMARY KEY,
                flow_id INTEGER NOT NULL REFERENCES remarketing_flows(id) ON DELETE CASCADE,
                step_order INTEGER NOT NULL DEFAULT 1,
                stage_name TEXT NOT NULL DEFAULT '',
                wait_minutes INTEGER NOT NULL DEFAULT 1440,
                template_id INTEGER REFERENCES message_templates(id) ON DELETE SET NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE (flow_id, step_order)
            )
        """))
        conn.execute(text("""ALTER TABLE remarketing_steps ADD COLUMN IF NOT EXISTS stage_name TEXT NOT NULL DEFAULT ''"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_remarketing_steps_flow_id ON remarketing_steps (flow_id)"""))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS remarketing_enrollments (
                id SERIAL PRIMARY KEY,
                flow_id INTEGER NOT NULL REFERENCES remarketing_flows(id) ON DELETE CASCADE,
                phone TEXT NOT NULL,
                current_step_order INTEGER NOT NULL DEFAULT 1,
                state TEXT NOT NULL DEFAULT 'active',
                enrolled_at TIMESTAMP NOT NULL DEFAULT NOW(),
                step_started_at TIMESTAMP NOT NULL DEFAULT NOW(),
                next_run_at TIMESTAMP NULL,
                last_sent_at TIMESTAMP NULL,
                last_sent_step_order INTEGER NULL,
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                meta_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                UNIQUE (flow_id, phone)
            )
        """))
        conn.execute(text("""ALTER TABLE remarketing_enrollments ADD COLUMN IF NOT EXISTS next_run_at TIMESTAMP NULL"""))
        conn.execute(text("""ALTER TABLE remarketing_enrollments ADD COLUMN IF NOT EXISTS last_sent_at TIMESTAMP NULL"""))
        conn.execute(text("""ALTER TABLE remarketing_enrollments ADD COLUMN IF NOT EXISTS last_sent_step_order INTEGER NULL"""))
        conn.execute(text("""ALTER TABLE remarketing_enrollments ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()"""))
        conn.execute(text("""ALTER TABLE remarketing_enrollments ADD COLUMN IF NOT EXISTS meta_json JSONB NOT NULL DEFAULT '{}'::jsonb"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_remarketing_enrollments_flow_state ON remarketing_enrollments (flow_id, state)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_remarketing_enrollments_state_next_run ON remarketing_enrollments (state, next_run_at)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_remarketing_enrollments_phone ON remarketing_enrollments (phone)"""))

        # -------------------------
        # security (policy + users + sessions + keys + audit)
        # -------------------------
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS security_policy (
                id INTEGER PRIMARY KEY,
                password_min_length INTEGER NOT NULL DEFAULT 10,
                require_special_chars BOOLEAN NOT NULL DEFAULT TRUE,
                access_token_minutes INTEGER NOT NULL DEFAULT 15,
                refresh_token_days INTEGER NOT NULL DEFAULT 15,
                session_idle_minutes INTEGER NOT NULL DEFAULT 30,
                session_absolute_hours INTEGER NOT NULL DEFAULT 12,
                max_failed_attempts INTEGER NOT NULL DEFAULT 5,
                lock_minutes INTEGER NOT NULL DEFAULT 15,
                force_password_rotation_days INTEGER NOT NULL DEFAULT 90,
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            INSERT INTO security_policy (
                id, password_min_length, require_special_chars, access_token_minutes, refresh_token_days,
                session_idle_minutes, session_absolute_hours, max_failed_attempts, lock_minutes,
                force_password_rotation_days, updated_at
            )
            VALUES (1, 10, TRUE, 15, 15, 30, 12, 5, 15, 90, NOW())
            ON CONFLICT (id) DO NOTHING
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS security_mfa_settings (
                id INTEGER PRIMARY KEY,
                enforce_for_admins BOOLEAN NOT NULL DEFAULT TRUE,
                enforce_for_supervisors BOOLEAN NOT NULL DEFAULT TRUE,
                allow_for_agents BOOLEAN NOT NULL DEFAULT FALSE,
                backup_codes_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            INSERT INTO security_mfa_settings (
                id, enforce_for_admins, enforce_for_supervisors, allow_for_agents, backup_codes_enabled, updated_at
            )
            VALUES (1, TRUE, TRUE, FALSE, TRUE, NOW())
            ON CONFLICT (id) DO NOTHING
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS security_alert_settings (
                id INTEGER PRIMARY KEY,
                failed_login_alert BOOLEAN NOT NULL DEFAULT TRUE,
                suspicious_ip_alert BOOLEAN NOT NULL DEFAULT TRUE,
                security_change_alert BOOLEAN NOT NULL DEFAULT TRUE,
                webhook_failure_alert BOOLEAN NOT NULL DEFAULT TRUE,
                channel_email BOOLEAN NOT NULL DEFAULT TRUE,
                channel_whatsapp BOOLEAN NOT NULL DEFAULT FALSE,
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            INSERT INTO security_alert_settings (
                id, failed_login_alert, suspicious_ip_alert, security_change_alert,
                webhook_failure_alert, channel_email, channel_whatsapp, updated_at
            )
            VALUES (1, TRUE, TRUE, TRUE, TRUE, TRUE, FALSE, NOW())
            ON CONFLICT (id) DO NOTHING
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS app_users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL DEFAULT 'agente',
                twofa BOOLEAN NOT NULL DEFAULT FALSE,
                twofa_secret_cipher TEXT NOT NULL DEFAULT '',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                password_salt TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL DEFAULT '',
                password_updated_at TIMESTAMP NULL,
                last_login_at TIMESTAMP NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""ALTER TABLE app_users ADD COLUMN IF NOT EXISTS password_salt TEXT NOT NULL DEFAULT ''"""))
        conn.execute(text("""ALTER TABLE app_users ADD COLUMN IF NOT EXISTS password_hash TEXT NOT NULL DEFAULT ''"""))
        conn.execute(text("""ALTER TABLE app_users ADD COLUMN IF NOT EXISTS password_updated_at TIMESTAMP NULL"""))
        conn.execute(text("""ALTER TABLE app_users ADD COLUMN IF NOT EXISTS twofa_secret_cipher TEXT NOT NULL DEFAULT ''"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_app_users_role ON app_users (role)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_app_users_active ON app_users (is_active)"""))

        conn.execute(text("""
            INSERT INTO app_users (name, email, role, twofa, is_active, created_at, updated_at)
            SELECT 'Administrador', 'admin@verane.com', 'admin', TRUE, TRUE, NOW(), NOW()
            WHERE NOT EXISTS (SELECT 1 FROM app_users)
        """))

        # Migración de contraseñas (si hay usuarios legacy sin hash).
        users_without_password = conn.execute(
            text(
                """
                SELECT id
                FROM app_users
                WHERE COALESCE(password_hash, '') = ''
                   OR COALESCE(password_salt, '') = ''
                ORDER BY id ASC
                LIMIT 2000
                """
            )
        ).mappings().all()
        bootstrap_password = str(os.getenv("SECURITY_BOOTSTRAP_ADMIN_PASSWORD", "Admin12345!") or "Admin12345!").strip()
        if not bootstrap_password:
            bootstrap_password = "Admin12345!"
        for u in users_without_password:
            uid = int(u.get("id") or 0)
            if uid <= 0:
                continue
            try:
                salt, pwh = _hash_password(bootstrap_password)
                conn.execute(
                    text(
                        """
                        UPDATE app_users
                        SET
                            password_salt = :salt,
                            password_hash = :pwh,
                            password_updated_at = NOW(),
                            updated_at = NOW()
                        WHERE id = :uid
                        """
                    ),
                    {"uid": uid, "salt": salt, "pwh": pwh},
                )
            except Exception:
                pass

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS app_user_sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
                device TEXT NOT NULL DEFAULT '',
                ip TEXT NOT NULL DEFAULT '',
                user_agent TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                last_seen_at TIMESTAMP NOT NULL DEFAULT NOW(),
                revoked_at TIMESTAMP NULL
            )
        """))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_app_user_sessions_user_id ON app_user_sessions (user_id)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_app_user_sessions_revoked ON app_user_sessions (revoked_at)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_app_user_sessions_last_seen ON app_user_sessions (last_seen_at DESC)"""))

        conn.execute(text("""
            INSERT INTO app_user_sessions (id, user_id, device, ip, user_agent, created_at, last_seen_at, revoked_at)
            SELECT
                'bootstrap-admin-session',
                u.id,
                'Chrome / Windows',
                '127.0.0.1',
                'bootstrap',
                NOW() - INTERVAL '45 minutes',
                NOW(),
                NULL
            FROM app_users u
            WHERE LOWER(TRIM(u.email)) = 'admin@verane.com'
              AND NOT EXISTS (SELECT 1 FROM app_user_sessions)
            LIMIT 1
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS app_api_keys (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                scope TEXT NOT NULL DEFAULT 'general',
                secret_preview TEXT NOT NULL DEFAULT '',
                secret_hash TEXT NOT NULL DEFAULT '',
                secret_cipher TEXT NOT NULL DEFAULT '',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                rotation_days INTEGER NOT NULL DEFAULT 90,
                next_rotation_at TIMESTAMP NULL,
                last_rotated_at TIMESTAMP NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""ALTER TABLE app_api_keys ADD COLUMN IF NOT EXISTS secret_cipher TEXT NOT NULL DEFAULT ''"""))
        conn.execute(text("""ALTER TABLE app_api_keys ADD COLUMN IF NOT EXISTS rotation_days INTEGER NOT NULL DEFAULT 90"""))
        conn.execute(text("""ALTER TABLE app_api_keys ADD COLUMN IF NOT EXISTS next_rotation_at TIMESTAMP NULL"""))
        conn.execute(text("""ALTER TABLE app_api_keys ADD COLUMN IF NOT EXISTS last_rotated_at TIMESTAMP NULL"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_app_api_keys_scope ON app_api_keys (scope)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_app_api_keys_active ON app_api_keys (is_active)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_app_api_keys_next_rotation ON app_api_keys (next_rotation_at)"""))
        conn.execute(text("""UPDATE app_api_keys SET rotation_days = 90 WHERE COALESCE(rotation_days, 0) <= 0"""))
        conn.execute(text("""
            INSERT INTO app_api_keys (name, scope, secret_preview, secret_hash, is_active, created_at, updated_at)
            SELECT
                'WhatsApp Cloud Token', 'mensajeria', 'wa_t...0001', md5('bootstrap-wa-token'), TRUE, NOW(), NOW()
            WHERE NOT EXISTS (SELECT 1 FROM app_api_keys)
        """))
        conn.execute(text("""
            INSERT INTO app_api_keys (name, scope, secret_preview, secret_hash, is_active, created_at, updated_at)
            SELECT
                'WooCommerce Consumer Key', 'catalogo', 'wc_k...0002', md5('bootstrap-wc-token'), TRUE, NOW(), NOW()
            WHERE (SELECT COUNT(1) FROM app_api_keys) = 1
        """))
        conn.execute(text("""
            INSERT INTO app_api_keys (name, scope, secret_preview, secret_hash, is_active, created_at, updated_at)
            SELECT
                'Proveedor IA Principal', 'inferencia', 'ia_k...0003', md5('bootstrap-ia-token'), TRUE, NOW(), NOW()
            WHERE (SELECT COUNT(1) FROM app_api_keys) = 2
        """))

        # Migración best-effort: si faltan secretos cifrados/rotación, regenera secreto interno.
        stale_keys = conn.execute(
            text(
                """
                SELECT id
                FROM app_api_keys
                WHERE COALESCE(secret_cipher, '') = ''
                   OR COALESCE(secret_hash, '') = ''
                   OR COALESCE(secret_preview, '') = ''
                   OR next_rotation_at IS NULL
                ORDER BY id ASC
                LIMIT 500
                """
            )
        ).mappings().all()

        for k in stale_keys:
            key_id = int(k.get("id") or 0)
            if key_id <= 0:
                continue
            try:
                plain_secret, preview, secret_hash, secret_cipher = _new_api_secret()
                conn.execute(
                    text(
                        """
                        UPDATE app_api_keys
                        SET
                            secret_preview = :preview,
                            secret_hash = :secret_hash,
                            secret_cipher = :secret_cipher,
                            last_rotated_at = COALESCE(last_rotated_at, NOW()),
                            next_rotation_at = COALESCE(next_rotation_at, NOW() + ((rotation_days::text || ' days')::interval)),
                            updated_at = NOW()
                        WHERE id = :key_id
                        """
                    ),
                    {
                        "key_id": key_id,
                        "preview": preview,
                        "secret_hash": secret_hash,
                        "secret_cipher": secret_cipher,
                    },
                )
            except Exception:
                # Nunca tumbamos el arranque por una clave con datos legacy.
                pass

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS security_audit_events (
                id BIGSERIAL PRIMARY KEY,
                level TEXT NOT NULL DEFAULT 'low',
                action TEXT NOT NULL,
                actor TEXT NOT NULL DEFAULT 'Sistema',
                ip TEXT NOT NULL DEFAULT '',
                details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_security_audit_level ON security_audit_events (level)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_security_audit_created_at ON security_audit_events (created_at DESC)"""))

        conn.execute(text("""
            INSERT INTO security_audit_events (level, action, actor, ip, details_json, created_at)
            SELECT 'low', 'Inicialización de módulo de seguridad', 'Sistema', '', '{}'::jsonb, NOW()
            WHERE NOT EXISTS (SELECT 1 FROM security_audit_events)
        """))
        # -------------------------
        # mobile push (FCM tokens + event log)
        # -------------------------
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mobile_push_tokens (
                id BIGSERIAL PRIMARY KEY,
                token TEXT NOT NULL UNIQUE,
                platform TEXT NOT NULL DEFAULT 'android',
                app_version TEXT NOT NULL DEFAULT '',
                device_id TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT 'agente',
                actor TEXT NOT NULL DEFAULT '',
                notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                last_seen_at TIMESTAMP NOT NULL DEFAULT NOW(),
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""ALTER TABLE mobile_push_tokens ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'agente'"""))
        conn.execute(text("""ALTER TABLE mobile_push_tokens ADD COLUMN IF NOT EXISTS actor TEXT NOT NULL DEFAULT ''"""))
        conn.execute(text("""ALTER TABLE mobile_push_tokens ADD COLUMN IF NOT EXISTS app_version TEXT NOT NULL DEFAULT ''"""))
        conn.execute(text("""ALTER TABLE mobile_push_tokens ADD COLUMN IF NOT EXISTS device_id TEXT NOT NULL DEFAULT ''"""))
        conn.execute(text("""ALTER TABLE mobile_push_tokens ADD COLUMN IF NOT EXISTS notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE"""))
        conn.execute(text("""ALTER TABLE mobile_push_tokens ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE"""))
        conn.execute(text("""ALTER TABLE mobile_push_tokens ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMP NOT NULL DEFAULT NOW()"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_mobile_push_tokens_active ON mobile_push_tokens (is_active, notifications_enabled, last_seen_at DESC)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_mobile_push_tokens_role ON mobile_push_tokens (role)"""))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mobile_push_events (
                id BIGSERIAL PRIMARY KEY,
                event_type TEXT NOT NULL DEFAULT 'generic',
                role_scope TEXT NOT NULL DEFAULT 'all',
                title TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL DEFAULT '',
                data_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                tokens_targeted INTEGER NOT NULL DEFAULT 0,
                tokens_sent INTEGER NOT NULL DEFAULT 0,
                tokens_failed INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'queued',
                error TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                delivered_at TIMESTAMP NULL
            )
        """))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_mobile_push_events_created ON mobile_push_events (created_at DESC)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_mobile_push_events_status ON mobile_push_events (status, created_at DESC)"""))


@app.on_event("startup")
def _startup():
    # Startup resiliente para evitar 503 por carrera de arranque con Postgres.
    raw_retries = str(os.getenv("DB_STARTUP_RETRIES", "20") or "20").strip()
    raw_delay = str(os.getenv("DB_STARTUP_DELAY_SEC", "2") or "2").strip()
    try:
        retries = max(1, min(int(raw_retries), 120))
    except Exception:
        retries = 20
    try:
        delay_sec = max(0.2, min(float(raw_delay), 10.0))
    except Exception:
        delay_sec = 2.0

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            ensure_schema()
            if attempt > 1:
                print(f"[STARTUP] ensure_schema recovered on attempt {attempt}/{retries}")
            return
        except Exception as e:
            last_error = e
            print(f"[STARTUP] ensure_schema failed attempt {attempt}/{retries}: {str(e)[:260]}")
            if attempt < retries:
                time.sleep(delay_sec)

    if last_error:
        raise last_error

async def _run_remarketing_engine_forever(stop_event: asyncio.Event, interval_sec: int) -> None:
    wait_sec = int(max(2, min(int(interval_sec or 8), 120)))
    while not stop_event.is_set():
        try:
            await process_due_remarketing()
        except Exception as e:
            print("[REMARKETING_ENGINE] tick error:", str(e)[:900])

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=wait_sec)
        except asyncio.TimeoutError:
            pass


@app.on_event("startup")
async def _startup_campaign_engine():
    global _campaign_engine_stop, _campaign_engine_task

    cfg = engine_settings()
    if not cfg.get("enabled"):
        print("[CAMPAIGN_ENGINE] disabled")
        return

    if _campaign_engine_task and not _campaign_engine_task.done():
        return

    _campaign_engine_stop = asyncio.Event()
    _campaign_engine_task = asyncio.create_task(run_campaign_engine_forever(_campaign_engine_stop))
    print(
        "[CAMPAIGN_ENGINE] started",
        {
            "interval_sec": cfg.get("interval_sec"),
            "batch_size": cfg.get("batch_size"),
            "send_delay_ms": cfg.get("send_delay_ms"),
        },
    )


@app.on_event("startup")
async def _startup_remarketing_engine_standalone():
    global _remarketing_engine_stop, _remarketing_engine_task

    if _remarketing_engine_task and not _remarketing_engine_task.done():
        return

    rmk_cfg = remarketing_settings()
    if not bool(rmk_cfg.get("enabled")):
        print("[REMARKETING_ENGINE] disabled (REMARKETING_ENGINE_ENABLED=false)")
        return

    raw_interval = str(os.getenv("REMARKETING_ENGINE_INTERVAL_SEC", "8") or "8").strip()
    try:
        interval_sec = int(raw_interval)
    except Exception:
        interval_sec = 8

    if interval_sec <= 0:
        print("[REMARKETING_ENGINE] standalone disabled (REMARKETING_ENGINE_INTERVAL_SEC <= 0)")
        return

    _remarketing_engine_stop = asyncio.Event()
    _remarketing_engine_task = asyncio.create_task(
        _run_remarketing_engine_forever(_remarketing_engine_stop, interval_sec=interval_sec)
    )
    print("[REMARKETING_ENGINE] standalone started", {"interval_sec": interval_sec})


@app.on_event("startup")
async def _startup_wc_cache_sync():
    global _wc_cache_sync_task

    if _wc_cache_sync_task and not _wc_cache_sync_task.done():
        return

    raw_interval = str(os.getenv("WC_CACHE_SYNC_INTERVAL_SEC", "0") or "0").strip()
    try:
        interval_sec = int(raw_interval)
    except Exception:
        interval_sec = 0

    if interval_sec <= 0:
        print("[WC_CACHE_SYNC] disabled (WC_CACHE_SYNC_INTERVAL_SEC <= 0)")
        return

    if not wc_enabled():
        print("[WC_CACHE_SYNC] disabled (Woo env vars not set)")
        return

    _wc_cache_sync_task = asyncio.create_task(start_periodic_sync(interval_sec=interval_sec))
    print("[WC_CACHE_SYNC] started", {"interval_sec": interval_sec})


@app.on_event("startup")
async def _startup_kb_web_sources_sync():
    global _kb_web_sync_task

    if _kb_web_sync_task and not _kb_web_sync_task.done():
        return

    raw_interval = str(os.getenv("KB_WEB_SYNC_INTERVAL_SEC", "180") or "180").strip()
    try:
        interval_sec = int(raw_interval)
    except Exception:
        interval_sec = 180

    if interval_sec <= 0:
        print("[KB_WEB_SYNC] disabled (KB_WEB_SYNC_INTERVAL_SEC <= 0)")
        return

    _kb_web_sync_task = asyncio.create_task(start_web_sources_sync_loop(interval_sec=interval_sec))
    print("[KB_WEB_SYNC] started", {"interval_sec": interval_sec})


async def _run_security_key_rotation_forever(stop_event: asyncio.Event, interval_sec: int) -> None:
    wait_sec = int(max(30, min(int(interval_sec or 900), 86400)))
    while not stop_event.is_set():
        try:
            rotate_due_security_keys_once(limit=60)
        except Exception as e:
            print("[SECURITY_ROTATION] tick error:", str(e)[:900])
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=wait_sec)
        except asyncio.TimeoutError:
            pass


@app.on_event("startup")
async def _startup_security_key_rotation():
    global _security_key_rotation_stop, _security_key_rotation_task

    cfg = security_rotation_settings()
    if not bool(cfg.get("enabled")):
        print("[SECURITY_ROTATION] disabled")
        return
    if _security_key_rotation_task and not _security_key_rotation_task.done():
        return

    _security_key_rotation_stop = asyncio.Event()
    _security_key_rotation_task = asyncio.create_task(
        _run_security_key_rotation_forever(_security_key_rotation_stop, interval_sec=int(cfg.get("interval_sec") or 900))
    )
    print("[SECURITY_ROTATION] started", cfg)


@app.on_event("shutdown")
async def _shutdown_campaign_engine():
    global _campaign_engine_stop, _campaign_engine_task

    if _campaign_engine_stop:
        _campaign_engine_stop.set()

    if _campaign_engine_task:
        try:
            await _campaign_engine_task
        except Exception:
            pass

    _campaign_engine_task = None
    _campaign_engine_stop = None


@app.on_event("shutdown")
async def _shutdown_remarketing_engine_standalone():
    global _remarketing_engine_stop, _remarketing_engine_task

    if _remarketing_engine_stop:
        _remarketing_engine_stop.set()

    if _remarketing_engine_task:
        try:
            await _remarketing_engine_task
        except Exception:
            pass

    _remarketing_engine_task = None
    _remarketing_engine_stop = None


@app.on_event("shutdown")
async def _shutdown_wc_cache_sync():
    global _wc_cache_sync_task

    if not _wc_cache_sync_task:
        return

    _wc_cache_sync_task.cancel()
    try:
        await _wc_cache_sync_task
    except asyncio.CancelledError:
        pass
    except Exception:
        pass
    _wc_cache_sync_task = None


@app.on_event("shutdown")
async def _shutdown_kb_web_sources_sync():
    global _kb_web_sync_task

    if not _kb_web_sync_task:
        return

    _kb_web_sync_task.cancel()
    try:
        await _kb_web_sync_task
    except asyncio.CancelledError:
        pass
    except Exception:
        pass
    _kb_web_sync_task = None


@app.on_event("shutdown")
async def _shutdown_security_key_rotation():
    global _security_key_rotation_stop, _security_key_rotation_task

    if _security_key_rotation_stop:
        _security_key_rotation_stop.set()

    if _security_key_rotation_task:
        try:
            await _security_key_rotation_task
        except Exception:
            pass

    _security_key_rotation_task = None
    _security_key_rotation_stop = None


# =========================================================
# MODELS (solo los que son de API/UI)
# =========================================================

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


class CustomerPatch(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    city: Optional[str] = None
    customer_type: Optional[str] = None
    interests: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    payment_status: Optional[str] = None
    payment_reference: Optional[str] = None


class SegmentIn(BaseModel):
    name: str
    rules_json: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class SegmentPatch(BaseModel):
    name: Optional[str] = None
    rules_json: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class LabelIn(BaseModel):
    name: str
    label_key: str = ""
    color: str = "#64748b"
    icon: str = "tag"
    description: str = ""
    is_active: bool = True


class LabelPatch(BaseModel):
    name: Optional[str] = None
    label_key: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class TemplateIn(BaseModel):
    name: str
    category: str = "general"
    channel: str = "whatsapp"
    body: str = ""
    variables_json: List[str] = Field(default_factory=list)
    blocks_json: List[Dict[str, Any]] = Field(default_factory=list)
    params_json: Dict[str, Any] = Field(default_factory=dict)
    render_mode: str = "chat"
    status: str = "draft"


class TemplatePatch(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    channel: Optional[str] = None
    body: Optional[str] = None
    variables_json: Optional[List[str]] = None
    blocks_json: Optional[List[Dict[str, Any]]] = None
    params_json: Optional[Dict[str, Any]] = None
    render_mode: Optional[str] = None
    status: Optional[str] = None


class TemplatePreviewIn(BaseModel):
    variables: Dict[str, Any] = Field(default_factory=dict)


class TemplateRenderIn(BaseModel):
    phone: str = ""
    campaign_id: Optional[int] = None
    overrides: Dict[str, Any] = Field(default_factory=dict)


class CampaignIn(BaseModel):
    name: str
    objective: str = ""
    segment_id: Optional[int] = None
    template_id: Optional[int] = None
    status: str = "draft"
    scheduled_at: Optional[datetime] = None
    channel: str = "whatsapp"


class CampaignPatch(BaseModel):
    name: Optional[str] = None
    objective: Optional[str] = None
    segment_id: Optional[int] = None
    template_id: Optional[int] = None
    status: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    channel: Optional[str] = None


class TriggerIn(BaseModel):
    name: str
    channel: str = "whatsapp"
    event_type: str = "message_in"
    trigger_type: str = "message_flow"
    flow_event: str = "received"
    conditions_json: Dict[str, Any] = Field(default_factory=dict)
    action_json: Dict[str, Any] = Field(default_factory=dict)
    cooldown_minutes: int = 60
    is_active: bool = True
    assistant_enabled: bool = False
    assistant_message_type: str = "auto"
    priority: int = 100
    block_ai: bool = True
    stop_on_match: bool = True
    only_when_no_takeover: bool = True


class TriggerPatch(BaseModel):
    name: Optional[str] = None
    channel: Optional[str] = None
    event_type: Optional[str] = None
    trigger_type: Optional[str] = None
    flow_event: Optional[str] = None
    conditions_json: Optional[Dict[str, Any]] = None
    action_json: Optional[Dict[str, Any]] = None
    cooldown_minutes: Optional[int] = None
    is_active: Optional[bool] = None
    assistant_enabled: Optional[bool] = None
    assistant_message_type: Optional[str] = None
    priority: Optional[int] = None
    block_ai: Optional[bool] = None
    stop_on_match: Optional[bool] = None
    only_when_no_takeover: Optional[bool] = None


class RemarketingFlowIn(BaseModel):
    name: str
    channel: str = "whatsapp"
    entry_rules_json: Dict[str, Any] = Field(default_factory=dict)
    exit_rules_json: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = False


class RemarketingFlowPatch(BaseModel):
    name: Optional[str] = None
    channel: Optional[str] = None
    entry_rules_json: Optional[Dict[str, Any]] = None
    exit_rules_json: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ChannelCopyIn(BaseModel):
    target_channel: str
    name_suffix: str = ""


class RemarketingStepIn(BaseModel):
    step_order: int = 1
    stage_name: str = ""
    wait_minutes: int = 1440
    template_id: Optional[int] = None


class RemarketingStepPatch(BaseModel):
    step_order: Optional[int] = None
    stage_name: Optional[str] = None
    wait_minutes: Optional[int] = None
    template_id: Optional[int] = None


class RemarketingStageAssignIn(BaseModel):
    phone: str
    flow_id: int
    stage: str = "s1"
    send_now: bool = True


class RemarketingDispatchIn(BaseModel):
    include_hold: bool = False
    limit: int = 600


# =========================================================
# HELPERS
# =========================================================

def _parse_tags_param(tags: str) -> List[str]:
    if not tags:
        return []
    out: List[str] = []
    for t in tags.split(","):
        tt = (t or "").strip().lower()
        if tt:
            out.append(tt)
    return out


def _split_tags_csv(raw: str) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in str(raw or "").split(","):
        token = str(item or "").strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def _join_tags_csv(tags: List[str]) -> str:
    out: List[str] = []
    seen = set()
    for item in tags:
        token = str(item or "").strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return ",".join(out)


def _normalize_label_key(raw: str, fallback: str = "") -> str:
    token = str(raw or "").strip().lower()
    token = re.sub(r"[^a-z0-9]+", "_", token)
    token = token.strip("_")
    if token:
        return token[:64]
    fb = str(fallback or "").strip().lower()
    fb = re.sub(r"[^a-z0-9]+", "_", fb).strip("_")
    return (fb[:64] or "label")


def _normalize_label_color(raw: str) -> str:
    val = str(raw or "").strip().lower()
    if re.fullmatch(r"#[0-9a-f]{6}", val):
        return val
    return "#64748b"


def _normalize_label_icon(raw: str) -> str:
    icon = str(raw or "").strip()
    if not icon:
        return "tag"
    return icon[:48]


def _parse_range_days(raw: str, default_days: int = 7, max_days: int = 365) -> int:
    token = (raw or "").strip().lower()
    if not token:
        return default_days

    if token.endswith("d"):
        token = token[:-1]

    try:
        days = int(token)
    except Exception:
        return default_days

    return max(1, min(days, max_days))


def _safe_json_dict(val: Any) -> Dict[str, Any]:
    if isinstance(val, dict):
        return val
    return {}


def _replace_tag_key_everywhere(conn, old_key: str, new_key: str) -> int:
    old = _normalize_label_key(old_key)
    new = _normalize_label_key(new_key)
    if not old or not new or old == new:
        return 0

    rows = conn.execute(
        text(
            """
            SELECT phone, COALESCE(tags, '') AS tags
            FROM conversations
            WHERE LOWER(COALESCE(tags, '')) LIKE :needle
            """
        ),
        {"needle": f"%{old}%"},
    ).mappings().all()

    changed = 0
    for row in rows:
        phone = str(row.get("phone") or "").strip()
        if not phone:
            continue
        tags = _split_tags_csv(str(row.get("tags") or ""))
        if old not in tags:
            continue
        replaced = [new if t == old else t for t in tags]
        next_csv = _join_tags_csv(replaced)
        if next_csv == _join_tags_csv(tags):
            continue
        conn.execute(
            text(
                """
                UPDATE conversations
                SET tags = :tags,
                    updated_at = NOW()
                WHERE phone = :phone
                """
            ),
            {"phone": phone, "tags": next_csv},
        )
        changed += 1
    return changed


def _remove_tag_key_everywhere(conn, key: str) -> int:
    tag_key = _normalize_label_key(key)
    if not tag_key:
        return 0

    rows = conn.execute(
        text(
            """
            SELECT phone, COALESCE(tags, '') AS tags
            FROM conversations
            WHERE LOWER(COALESCE(tags, '')) LIKE :needle
            """
        ),
        {"needle": f"%{tag_key}%"},
    ).mappings().all()

    changed = 0
    for row in rows:
        phone = str(row.get("phone") or "").strip()
        if not phone:
            continue
        tags = _split_tags_csv(str(row.get("tags") or ""))
        filtered = [t for t in tags if t != tag_key]
        next_csv = _join_tags_csv(filtered)
        if next_csv == _join_tags_csv(tags):
            continue
        conn.execute(
            text(
                """
                UPDATE conversations
                SET tags = :tags,
                    updated_at = NOW()
                WHERE phone = :phone
                """
            ),
            {"phone": phone, "tags": next_csv},
        )
        changed += 1
    return changed


def _normalize_status(raw: str, allowed: set[str], default: str) -> str:
    v = (raw or "").strip().lower()
    if v in allowed:
        return v
    return default


SUPPORTED_CHANNELS = {"whatsapp", "facebook", "instagram", "tiktok"}


def _normalize_channel(raw: str, default: str = "whatsapp") -> str:
    v = (raw or "").strip().lower()
    if v in SUPPORTED_CHANNELS:
        return v
    return default


def _normalize_event_type(raw: str) -> str:
    v = (raw or "").strip().lower()
    if not v:
        return "message_in"
    aliases = {
        "in": "message_in",
        "incoming": "message_in",
        "recibido": "message_in",
        "received": "message_in",
        "flow": "message_in",
        "comentario": "comment_in",
        "comment": "comment_in",
        "comment_incoming": "comment_in",
        "incoming_comment": "comment_in",
    }
    v = aliases.get(v, v)
    allowed = {"message_in", "message_out", "comment_in", "all", "*"}
    return v if v in allowed else "message_in"


def _normalize_trigger_type(raw: str) -> str:
    v = (raw or "").strip().lower()
    aliases = {
        "ninguna": "none",
        "etiqueta cambiada": "tag_changed",
        "logica": "logic",
        "lógica": "logic",
        "flujo de mensajes": "message_flow",
        "flujo de comentarios": "comment_flow",
        "tiempo": "time",
    }
    v = aliases.get(v, v)
    allowed = {"none", "tag_changed", "logic", "message_flow", "comment_flow", "time"}
    return v if v in allowed else "message_flow"


def _normalize_flow_event(raw: str) -> str:
    v = (raw or "").strip().lower()
    aliases = {
        "recibido": "received",
        "enviado": "sent",
        "envian y reciben": "both",
        "enviados_y_recibidos": "both",
    }
    v = aliases.get(v, v)
    allowed = {"received", "sent", "both"}
    return v if v in allowed else "received"


def _normalize_assistant_message_type(raw: str) -> str:
    v = (raw or "").strip().lower()
    aliases = {
        "texto": "text",
        "audio": "audio",
        "auto": "auto",
    }
    v = aliases.get(v, v)
    allowed = {"auto", "text", "audio"}
    return v if v in allowed else "auto"


PERFUME_RELATED_INTENTS = {
    "PRODUCT_SEARCH",
    "PREFERENCE_RECO",
    "PRICE_STOCK",
    "BUY_FLOW",
    "COMPARE",
    "PHOTO_REQUEST",
    "CHOICE",
}

PERFUME_TERMS = [
    "perfume",
    "colonia",
    "fragancia",
    "dior",
    "versace",
    "lattafa",
    "armaf",
    "carolina herrera",
    "paco rabanne",
    "chanel",
    "givenchy",
    "ysl",
    "sauvage",
    "invictus",
    "one million",
    "eros",
    "le male",
    "bleu de chanel",
    "212",
]


def _normalize_text_plain(raw: str) -> str:
    text_value = str(raw or "").strip().lower()
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
    }
    for src, dst in replacements.items():
        text_value = text_value.replace(src, dst)
    text_value = re.sub(r"\s+", " ", text_value).strip()
    return text_value


def _extract_perfume_terms(raw: str) -> List[str]:
    t = _normalize_text_plain(raw)
    if not t:
        return []
    found: List[str] = []
    for term in PERFUME_TERMS:
        if term in t:
            found.append(term)
    return found


def _is_perfume_related_intent(intent: str) -> bool:
    return str(intent or "").strip().upper() in PERFUME_RELATED_INTENTS


def _render_template(body: str, variables: Dict[str, Any]) -> str:
    out = body or ""
    if not variables:
        return out

    for k, v in variables.items():
        key = (k or "").strip()
        if not key:
            continue
        out = out.replace(f"{{{{{key}}}}}", str(v if v is not None else ""))
    return out


def _template_params_catalog() -> List[Dict[str, str]]:
    return [
        {"key": "business_name", "label": "Nombre del negocio"},
        {"key": "business_phone", "label": "Telefono del negocio"},
        {"key": "business_email", "label": "Correo del negocio"},
        {"key": "assistant_name", "label": "Nombre del Asistente"},
        {"key": "assistant_phone", "label": "Telefono del Asistente"},
        {"key": "customer_name", "label": "Nombre del cliente"},
        {"key": "customer_country", "label": "Pais del cliente"},
        {"key": "customer_phone", "label": "Telefono del cliente"},
        {"key": "customer_tag", "label": "Etiqueta del cliente"},
        {"key": "campaign_name", "label": "Anuncio"},
        {"key": "first_message_date", "label": "Fecha primer mensaje"},
        {"key": "last_message_date", "label": "Fecha ultimo mensaje"},
        {"key": "nombre", "label": "Nombre (alias)"},
        {"key": "phone", "label": "Telefono (alias)"},
        {"key": "city", "label": "Ciudad"},
        {"key": "payment_status", "label": "Estado de pago"},
    ]


def _normalize_template_blocks(raw_blocks: Any, body_fallback: str = "") -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    raw_list = raw_blocks if isinstance(raw_blocks, list) else []

    for item in raw_list:
        if not isinstance(item, dict):
            continue

        kind = str(item.get("kind") or item.get("type") or "text").strip().lower()
        delay_ms = item.get("delay_ms", 0)
        try:
            delay_ms = int(delay_ms)
        except Exception:
            delay_ms = 0
        delay_ms = max(0, min(delay_ms, 60000))

        if kind in ("image", "video", "audio"):
            media_id = str(item.get("media_id") or "").strip()
            media_url = str(
                item.get(f"{kind}_url")
                or item.get("media_url")
                or item.get("url")
                or ""
            ).strip()
            caption = str(item.get("caption") or item.get("text") or "").strip() if kind in ("image", "video") else ""
            if not media_id and not media_url:
                continue
            block = {
                "kind": kind,
                "media_id": media_id,
                "delay_ms": delay_ms,
            }
            if kind == "image":
                block["image_url"] = media_url
            elif kind == "video":
                block["video_url"] = media_url
            else:
                block["audio_url"] = media_url
            if kind in ("image", "video"):
                block["caption"] = caption
            blocks.append(block)
            continue

        text_val = str(item.get("text") or item.get("content") or item.get("body") or "").strip()
        if not text_val:
            continue
        blocks.append({"kind": "text", "text": text_val, "delay_ms": delay_ms})

    if blocks:
        return blocks

    fallback = str(body_fallback or "").strip()
    if fallback:
        return [{"kind": "text", "text": fallback, "delay_ms": 0}]
    return []


def _collect_missing_params(text_val: str, resolved: Dict[str, Any]) -> List[str]:
    import re

    missing: List[str] = []
    for token in re.findall(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", text_val or ""):
        key = (token or "").strip()
        if not key:
            continue
        v = resolved.get(key)
        if v is None or str(v).strip() == "":
            if key not in missing:
                missing.append(key)
    return missing


def _segment_filter_sql(rules: Dict[str, Any], prefix: str = "r") -> tuple[str, Dict[str, Any]]:
    rules = rules if isinstance(rules, dict) else {}
    conds: List[str] = []
    params: Dict[str, Any] = {}

    tag = str(rules.get("tag") or "").strip().lower()
    if tag:
        params[f"{prefix}_tag"] = f"%{tag}%"
        conds.append(f"LOWER(COALESCE(c.tags,'')) LIKE :{prefix}_tag")

    intent = str(rules.get("intent") or "").strip().upper()
    if intent:
        params[f"{prefix}_intent"] = intent
        conds.append(f"UPPER(COALESCE(c.intent_current,'')) = :{prefix}_intent")

    payment_status = str(rules.get("payment_status") or "").strip().lower()
    if payment_status:
        params[f"{prefix}_payment"] = payment_status
        conds.append(f"LOWER(COALESCE(c.payment_status,'')) = :{prefix}_payment")

    takeover = rules.get("takeover")
    if isinstance(takeover, bool):
        params[f"{prefix}_takeover"] = takeover
        conds.append(f"c.takeover = :{prefix}_takeover")

    city = str(rules.get("city") or "").strip().lower()
    if city:
        params[f"{prefix}_city"] = f"%{city}%"
        conds.append(f"LOWER(COALESCE(c.city,'')) LIKE :{prefix}_city")

    if not conds:
        return "TRUE", params
    return " AND ".join(conds), params


# =========================================================
# ENDPOINTS
# =========================================================

@app.get("/api/health")
def health():
    return {"ok": True, "build": "2026-02-22-api-main-clean-1"}


# -------------------------
# Woo endpoints UI
# -------------------------

@app.get("/api/wc/products")
async def wc_products(
    q: str = Query("", description="texto de búsqueda"),
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
):
    params = {"search": q or "", "page": page, "per_page": per_page, "status": "publish"}
    data = await wc_get("/products", params=params)
    items = [map_product_for_ui(p) for p in (data or [])]
    return {"products": items}


@app.post("/api/wc/send-product")
async def send_wc_product(payload: dict):
    phone = payload.get("phone")
    product_id = payload.get("product_id")
    custom_caption = payload.get("caption", "")

    if not phone or not product_id:
        raise HTTPException(status_code=400, detail="phone and product_id required")

    wa = await wc_send_product(
        phone=str(phone),
        product_id=int(product_id),
        custom_caption=str(custom_caption or ""),
    )

    return {"ok": True, "sent": bool(wa.get("sent")), "wa": wa}


@app.get("/api/wc/cache/sync-state")
def wc_cache_sync_state():
    return {
        "sync": get_wc_sync_state(),
        "cache": get_cache_stats(),
        "auto_sync_interval_sec": int(max(0, int(os.getenv("WC_CACHE_SYNC_INTERVAL_SEC", "0") or 0))),
        "full_sync_hours": int(max(1, int(os.getenv("WC_CACHE_FULL_SYNC_HOURS", "24") or 24))),
    }


@app.post("/api/wc/cache/sync-now")
async def wc_cache_sync_now(
    mode: str = Query("recent", description="recent|full"),
    per_page: int = Query(100, ge=10, le=200),
):
    m = (mode or "recent").strip().lower()
    if not wc_enabled():
        raise HTTPException(status_code=400, detail="WooCommerce no está configurado")
    if m not in {"recent", "full"}:
        raise HTTPException(status_code=400, detail="mode must be recent|full")

    if m == "full":
        result = await sync_all_products_once(per_page=per_page, max_pages=2000)
    else:
        result = await sync_recent_products_once(per_page=per_page, max_pages=40)

    return {
        "ok": True,
        "mode": m,
        "result": result,
        "sync": get_wc_sync_state(),
        "cache": get_cache_stats(),
    }


# -------------------------
# Media upload (UI)
# -------------------------

@app.post("/api/media/upload")
async def upload_media(file: UploadFile = File(...), kind: str = Form("image")):
    import tempfile
    import subprocess

    kind = (kind or "image").lower().strip()
    if kind not in ("image", "video", "audio", "document"):
        raise HTTPException(status_code=400, detail="Invalid kind")

    content = await file.read()
    mime = (file.content_type or "application/octet-stream").split(";")[0].strip().lower()
    filename = file.filename or "upload"

    # Si suben webm (browser), lo convertimos a ogg/opus para WhatsApp
    if kind == "audio" and mime == "audio/webm":
        with tempfile.TemporaryDirectory() as tmp:
            in_path = os.path.join(tmp, "in.webm")
            out_path = os.path.join(tmp, "out.ogg")

            with open(in_path, "wb") as f:
                f.write(content)

            cmd = ["ffmpeg", "-y", "-i", in_path, "-c:a", "libopus", "-b:a", "24k", "-vn", out_path]
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if p.returncode != 0:
                err = p.stderr.decode("utf-8", errors="ignore")
                raise HTTPException(status_code=500, detail=f"ffmpeg convert failed: {err[:900]}")

            with open(out_path, "rb") as f:
                content = f.read()

        mime = "audio/ogg"
        filename = "audio.ogg"

    media_id = await upload_whatsapp_media(content, mime)
    return {"ok": True, "media_id": media_id, "mime_type": mime, "filename": filename, "kind": kind}


# -------------------------
# Conversations / CRM
# -------------------------

@app.post("/api/conversations/{phone}/read")
def mark_conversation_read(phone: str):
    phone = (phone or "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="phone required")

    ts = datetime.utcnow()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO conversations (phone, last_read_at)
            VALUES (:phone, :ts)
            ON CONFLICT (phone)
            DO UPDATE SET last_read_at = EXCLUDED.last_read_at
        """), {"phone": phone, "ts": ts})

    return {"ok": True}


@app.get("/api/crm/tags")
def list_crm_tags(limit: int = Query(200, ge=1, le=2000)):
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT DISTINCT TRIM(LOWER(x)) AS tag
            FROM conversations c
            CROSS JOIN LATERAL regexp_split_to_table(COALESCE(c.tags,''), ',') AS x
            WHERE TRIM(x) <> ''
            ORDER BY tag ASC
            LIMIT :limit
        """), {"limit": limit}).mappings().all()

    return {"tags": [r["tag"] for r in rows]}


@app.get("/api/conversations")
def get_conversations(
    search: str = Query("", description="Buscar por phone, nombre CRM o texto preview"),
    takeover: str = Query("all", description="all|on|off"),
    unread: str = Query("all", description="all|yes|no"),
    tags: str = Query("", description="Filtro por tags CRM. Ej: vip,pago pendiente"),
    channel: str = Query("all", description="whatsapp|facebook|instagram|tiktok|all"),
):
    takeover = (takeover or "all").strip().lower()
    unread = (unread or "all").strip().lower()
    channel = (channel or "whatsapp").strip().lower()
    term = (search or "").strip().lower()
    tag_list = _parse_tags_param(tags)

    where = []
    params: Dict[str, Any] = {}
    channel_filter_sql = ""
    if channel != "all":
        params["channel"] = _normalize_channel(channel, default="whatsapp")
        channel_filter_sql = "AND LOWER(COALESCE(mi.channel, 'whatsapp')) = :channel"

    if takeover == "on":
        where.append("c.takeover = TRUE")
    elif takeover == "off":
        where.append("c.takeover = FALSE")

    if term:
        params["term"] = f"%{term}%"
        where.append("""
            (
              LOWER(c.phone) LIKE :term
              OR LOWER(COALESCE(c.first_name,'') || ' ' || COALESCE(c.last_name,'')) LIKE :term
              OR LOWER(COALESCE(m.text, '')) LIKE :term
            )
        """)

    if tag_list:
        tag_clauses = []
        for i, t in enumerate(tag_list):
            k = f"tag{i}"
            params[k] = f"%{t}%"
            tag_clauses.append(f"LOWER(COALESCE(c.tags,'')) LIKE :{k}")
        where.append("(" + " OR ".join(tag_clauses) + ")")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    if unread in ("yes", "no"):
        unread_cond = """
            EXISTS (
                SELECT 1
                FROM messages mi
                WHERE mi.phone = c.phone
                  {channel_filter_sql}
                  AND mi.direction = 'in'
                  AND mi.created_at > COALESCE(c.last_read_at, TIMESTAMP 'epoch')
            )
        """.replace("{channel_filter_sql}", channel_filter_sql)
        extra = f" AND {unread_cond} " if unread == "yes" else f" AND NOT ({unread_cond}) "

        if where_sql:
            where_sql = where_sql + extra
        else:
            where_sql = "WHERE 1=1 " + extra

    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT
                c.phone,
                c.takeover,
                c.updated_at,
                c.first_name,
                c.last_name,
                c.city,
                c.customer_type,
                c.interests,
                c.tags,
                c.notes,
                c.last_read_at,

                m.text AS last_text,
                m.msg_type AS last_msg_type,
                m.direction AS last_direction,
                m.channel AS last_channel,
                m.created_at AS last_created_at,

                EXISTS (
                    SELECT 1
                    FROM messages mi
                    WHERE mi.phone = c.phone
                      {channel_filter_sql}
                      AND mi.direction = 'in'
                      AND mi.created_at > COALESCE(c.last_read_at, TIMESTAMP 'epoch')
                ) AS has_unread,

                (
                    SELECT COUNT(*)
                    FROM messages mi2
                    WHERE mi2.phone = c.phone
                      {channel_filter_sql_2}
                      AND mi2.direction = 'in'
                      AND mi2.created_at > COALESCE(c.last_read_at, TIMESTAMP 'epoch')
                ) AS unread_count

            FROM conversations c
            LEFT JOIN LATERAL (
                SELECT text, msg_type, direction, channel, created_at
                FROM messages
                WHERE phone = c.phone
                  {channel_filter_sql_3}
                ORDER BY created_at DESC
                LIMIT 1
            ) m ON TRUE

            {where_sql}

            ORDER BY c.updated_at DESC
            LIMIT 200
        """
            .replace("{channel_filter_sql}", channel_filter_sql)
            .replace("{channel_filter_sql_2}", channel_filter_sql.replace("mi.", "mi2."))
            .replace("{channel_filter_sql_3}", channel_filter_sql.replace("mi.", ""))
            .replace("{where_sql}", where_sql)
        ), params).mappings().all()

    out = []
    for r in rows:
        d = dict(r)
        d["text"] = d.get("last_text") or ""
        try:
            d["unread_count"] = int(d.get("unread_count") or 0)
        except Exception:
            d["unread_count"] = 0
        d["has_unread"] = bool(d.get("has_unread"))
        out.append(d)

    return {"conversations": out}


@app.get("/api/conversations/{phone}/messages")
def get_messages(
    phone: str,
    channel: str = Query("all", description="whatsapp|facebook|instagram|tiktok|all"),
):
    channel = (channel or "whatsapp").strip().lower()
    params: Dict[str, Any] = {"phone": phone}
    where_channel = ""
    if channel != "all":
        params["channel"] = _normalize_channel(channel, default="whatsapp")
        where_channel = "AND LOWER(COALESCE(channel, 'whatsapp')) = :channel"

    with engine.begin() as conn:
        rows = conn.execute(text("""
            WITH latest AS (
                SELECT
                    id, phone, direction, msg_type, text,
                    media_url, media_caption, media_id, mime_type, file_name, file_size, duration_sec,
                    featured_image, real_image, permalink, created_at,
                    extracted_text, ai_meta,
                    wa_message_id, wa_status, wa_error, wa_ts_sent, wa_ts_delivered, wa_ts_read
                FROM messages
                WHERE phone = :phone
                  {where_channel}
                ORDER BY created_at DESC
                LIMIT 500
            )
            SELECT *
            FROM latest
            ORDER BY created_at ASC
        """.replace("{where_channel}", where_channel)), params).mappings().all()

    return {"messages": [dict(r) for r in rows]}


# -------------------------
# Ingest (core pipeline)
# -------------------------

@app.post("/api/messages/ingest")
async def ingest(msg: IngestMessage):
    result = await run_ingest(msg)

    try:
        direction = str(msg.direction or "in").strip().lower()
        channel = _normalize_channel(str(msg.channel or "whatsapp"), default="whatsapp")
        msg_type = str(msg.msg_type or "text").strip().lower()
        reason = str((result or {}).get("reason") or "").strip().lower()

        # Push solo para inbound reales (no duplicados descartados)
        if direction == "in" and reason != "idempotency_skip_duplicate":
            preview = str(msg.text or msg.media_caption or "").strip()
            if len(preview) > 120:
                preview = preview[:117] + "..."
            if not preview:
                preview = f"[{msg_type or 'mensaje'}]"

            _emit_mobile_push_event(
                event_type="message_in",
                title=f"Nuevo mensaje ({channel})",
                body=f"{msg.phone}: {preview}",
                data={
                    "phone": str(msg.phone or ""),
                    "channel": channel,
                    "msg_type": msg_type,
                    "direction": "in",
                    "channel_id": "verane_messages",
                },
                role_scope="all",
            )
    except Exception as e:
        print("[PUSH] message_in event error:", str(e)[:400])

    return result


@app.post("/api/conversations/takeover")
def set_takeover(payload: TakeoverPayload):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO conversations (phone, takeover, updated_at)
            VALUES (:phone, :takeover, :updated_at)
            ON CONFLICT (phone)
            DO UPDATE SET takeover = EXCLUDED.takeover,
                          updated_at = EXCLUDED.updated_at
        """), {"phone": payload.phone, "takeover": payload.takeover, "updated_at": datetime.utcnow()})

    try:
        _emit_mobile_push_event(
            event_type="takeover_changed",
            title="Cambio de takeover",
            body=f"{payload.phone}: takeover {'ON' if payload.takeover else 'OFF'}",
            data={
                "phone": str(payload.phone or ""),
                "takeover": "on" if payload.takeover else "off",
                "channel_id": "verane_system",
            },
            role_scope="admin_supervisor",
        )
    except Exception as e:
        print("[PUSH] takeover event error:", str(e)[:400])
    return {"ok": True}


@app.post("/api/mobile/push/register")
def register_mobile_push_token(payload: "MobilePushRegisterIn"):
    token = _normalize_mobile_push_token(payload.token)
    if not token:
        raise HTTPException(status_code=400, detail="invalid push token")

    role = _normalize_mobile_role(payload.role)
    platform = str(payload.platform or "android").strip().lower()[:40] or "android"
    app_version = str(payload.app_version or "").strip()[:80]
    device_id = str(payload.device_id or "").strip()[:200]
    actor = str(payload.actor or "").strip()[:120]

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO mobile_push_tokens (
                    token, platform, app_version, device_id, role, actor,
                    notifications_enabled, is_active, last_seen_at, created_at, updated_at
                )
                VALUES (
                    :token, :platform, :app_version, :device_id, :role, :actor,
                    :notifications_enabled, TRUE, NOW(), NOW(), NOW()
                )
                ON CONFLICT (token) DO UPDATE SET
                    platform = EXCLUDED.platform,
                    app_version = EXCLUDED.app_version,
                    device_id = EXCLUDED.device_id,
                    role = EXCLUDED.role,
                    actor = EXCLUDED.actor,
                    notifications_enabled = EXCLUDED.notifications_enabled,
                    is_active = TRUE,
                    last_seen_at = NOW(),
                    updated_at = NOW()
                """
            ),
            {
                "token": token,
                "platform": platform,
                "app_version": app_version,
                "device_id": device_id,
                "role": role,
                "actor": actor,
                "notifications_enabled": bool(payload.notifications_enabled),
            },
        )

    return {"ok": True, "registered": True, "role": role}


@app.post("/api/push/register")
def register_mobile_push_token_compat(payload: "MobilePushRegisterIn"):
    return register_mobile_push_token(payload)


@app.post("/api/mobile/push/unregister")
def unregister_mobile_push_token(payload: "MobilePushUnregisterIn"):
    token = _normalize_mobile_push_token(payload.token)
    if not token:
        raise HTTPException(status_code=400, detail="invalid push token")

    with engine.begin() as conn:
        rs = conn.execute(
            text(
                """
                UPDATE mobile_push_tokens
                SET is_active = FALSE, updated_at = NOW()
                WHERE token = :token
                """
            ),
            {"token": token},
        )
    return {"ok": True, "unregistered": int(rs.rowcount or 0)}


@app.post("/api/push/unregister")
def unregister_mobile_push_token_compat(payload: "MobilePushUnregisterIn"):
    return unregister_mobile_push_token(payload)


@app.get("/api/mobile/push/state")
def mobile_push_state(request: StarletteRequest = None):
    _require_security_role(request, {"admin", "supervisor"})
    with engine.begin() as conn:
        summary = conn.execute(
            text(
                """
                SELECT
                    COUNT(*) FILTER (WHERE is_active = TRUE AND notifications_enabled = TRUE) AS active_total,
                    COUNT(*) FILTER (WHERE is_active = TRUE AND notifications_enabled = TRUE AND LOWER(role) = 'admin') AS active_admin,
                    COUNT(*) FILTER (WHERE is_active = TRUE AND notifications_enabled = TRUE AND LOWER(role) = 'supervisor') AS active_supervisor,
                    COUNT(*) FILTER (WHERE is_active = TRUE AND notifications_enabled = TRUE AND LOWER(role) = 'agente') AS active_agente
                FROM mobile_push_tokens
                """
            )
        ).mappings().first() or {}

        events = conn.execute(
            text(
                """
                SELECT
                    id, event_type, role_scope, title, status,
                    tokens_targeted, tokens_sent, tokens_failed,
                    error, created_at, delivered_at
                FROM mobile_push_events
                ORDER BY created_at DESC, id DESC
                LIMIT 80
                """
            )
        ).mappings().all()

    return {"summary": dict(summary), "events": [dict(r) for r in events]}


@app.get("/api/push/state")
def mobile_push_state_compat(request: StarletteRequest = None):
    return mobile_push_state(request=request)


@app.post("/api/mobile/push/test")
def test_mobile_push(payload: "MobilePushTestIn", request: StarletteRequest = None):
    _require_security_role(request, {"admin", "supervisor"})
    role_scope = _normalize_push_role_scope(payload.role_scope)
    result = _emit_mobile_push_event(
        event_type=str(payload.event_type or "manual_test"),
        title=str(payload.title or "Prueba push"),
        body=str(payload.body or "Push de prueba"),
        data={**(payload.data or {}), "channel_id": "verane_system", "test": "true"},
        role_scope=role_scope,
    )
    return {"ok": True, "result": result}


@app.post("/api/push/test")
def test_mobile_push_compat(payload: "MobilePushTestIn", request: StarletteRequest = None):
    return test_mobile_push(payload=payload, request=request)


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
    phone = (phone or "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="phone required")

    try:
        with engine.begin() as conn:
            r = conn.execute(text("""
                SELECT
                    phone,
                    takeover,
                    first_name,
                    last_name,
                    city,
                    customer_type,
                    interests,
                    tags,
                    notes,
                    COALESCE(intent_current, '') AS intent_current,
                    COALESCE(intent_stage, '') AS intent_stage,
                    COALESCE(payment_status, '') AS payment_status,
                    COALESCE(payment_reference, '') AS payment_reference,
                    COALESCE(crm_meta, '{}'::jsonb) AS crm_meta
                FROM conversations
                WHERE phone = :phone
            """), {"phone": phone}).mappings().first()

        if not r:
            return {
                "phone": phone,
                "takeover": False,
                "first_name": "",
                "last_name": "",
                "city": "",
                "customer_type": "",
                "interests": "",
                "tags": "",
                "notes": "",
                "intent_current": "",
                "intent_stage": "",
                "payment_status": "",
                "payment_reference": "",
                "crm_meta": {},
                "memory_summary": "",
            }

        data = dict(r)
        crm_meta = data.get("crm_meta") if isinstance(data.get("crm_meta"), dict) else {}
        ai_memory = crm_meta.get("ai_memory") if isinstance(crm_meta, dict) else {}
        data["memory_summary"] = str((ai_memory or {}).get("summary") or "").strip()
        return data

    except Exception as e:
        return {"ok": False, "error": str(e), "phone": phone}


# =========================================================
# Dashboard
# =========================================================

@app.get("/api/dashboard/overview")
def dashboard_overview(range: str = Query("7d")):
    days = _parse_range_days(range, default_days=7, max_days=365)
    since = datetime.utcnow() - timedelta(days=days)

    with engine.begin() as conn:
        r = conn.execute(text("""
            SELECT
                (SELECT COUNT(*) FROM conversations) AS conversations_total,
                (SELECT COUNT(*) FROM conversations WHERE updated_at >= :since) AS active_conversations,
                (SELECT COUNT(*) FROM conversations WHERE takeover = TRUE) AS takeover_on,
                (
                    SELECT COUNT(*)
                    FROM conversations c
                    WHERE EXISTS (
                        SELECT 1
                        FROM messages mi
                        WHERE mi.phone = c.phone
                          AND mi.direction = 'in'
                          AND mi.created_at > COALESCE(c.last_read_at, TIMESTAMP 'epoch')
                    )
                ) AS unread_conversations,
                (SELECT COUNT(*) FROM messages WHERE direction = 'in' AND created_at >= :since) AS messages_in,
                (SELECT COUNT(*) FROM messages WHERE direction = 'out' AND created_at >= :since) AS messages_out,
                (
                    SELECT COUNT(*)
                    FROM (
                        SELECT phone, MIN(created_at) AS first_seen
                        FROM messages
                        WHERE direction = 'in'
                        GROUP BY phone
                    ) f
                    WHERE f.first_seen >= :since
                ) AS new_customers,
                (
                    SELECT COUNT(*)
                    FROM campaigns
                    WHERE LOWER(status) IN ('running', 'scheduled')
                ) AS campaigns_live
        """), {"since": since}).mappings().first()

    data = dict(r or {})
    msg_in = int(data.get("messages_in") or 0)
    msg_out = int(data.get("messages_out") or 0)
    response_rate = round((msg_out / msg_in) * 100, 2) if msg_in > 0 else 0.0

    return {
        "range_days": days,
        "since": since,
        "kpis": {
            "conversations_total": int(data.get("conversations_total") or 0),
            "active_conversations": int(data.get("active_conversations") or 0),
            "new_customers": int(data.get("new_customers") or 0),
            "unread_conversations": int(data.get("unread_conversations") or 0),
            "takeover_on": int(data.get("takeover_on") or 0),
            "campaigns_live": int(data.get("campaigns_live") or 0),
            "messages_in": msg_in,
            "messages_out": msg_out,
            "response_rate_pct": response_rate,
        },
    }


@app.get("/api/dashboard/funnel")
def dashboard_funnel():
    with engine.begin() as conn:
        r = conn.execute(text("""
            SELECT
                COUNT(*) AS contacted,
                COUNT(*) FILTER (
                    WHERE UPPER(COALESCE(intent_current,'')) IN (
                        'PRODUCT_SEARCH',
                        'PREFERENCE_RECO',
                        'PRICE_STOCK',
                        'VARIANT_SELECTION'
                    )
                ) AS interest,
                COUNT(*) FILTER (
                    WHERE UPPER(COALESCE(intent_current,'')) = 'BUY_FLOW'
                ) AS buy_intent,
                COUNT(*) FILTER (
                    WHERE LOWER(COALESCE(payment_status,'')) IN ('pending', 'initiated', 'awaiting', 'processing')
                ) AS payment_pending,
                COUNT(*) FILTER (
                    WHERE LOWER(COALESCE(payment_status,'')) IN ('paid', 'completed', 'approved', 'success')
                ) AS paid
            FROM conversations
        """)).mappings().first()

    d = dict(r or {})
    contacted = int(d.get("contacted") or 0)
    interest = int(d.get("interest") or 0)
    buy_intent = int(d.get("buy_intent") or 0)
    payment_pending = int(d.get("payment_pending") or 0)
    paid = int(d.get("paid") or 0)

    def _ratio(num: int, den: int) -> float:
        if den <= 0:
            return 0.0
        return round((num / den) * 100, 2)

    return {
        "steps": [
            {"id": "contacted", "label": "Contactados", "value": contacted, "pct_prev": 100.0},
            {"id": "interest", "label": "Interes", "value": interest, "pct_prev": _ratio(interest, contacted)},
            {"id": "buy_intent", "label": "Intencion de compra", "value": buy_intent, "pct_prev": _ratio(buy_intent, interest)},
            {"id": "payment_pending", "label": "Pago pendiente", "value": payment_pending, "pct_prev": _ratio(payment_pending, buy_intent)},
            {"id": "paid", "label": "Pago confirmado", "value": paid, "pct_prev": _ratio(paid, payment_pending)},
        ]
    }


@app.get("/api/dashboard/campaigns")
def dashboard_campaigns(range: str = Query("30d")):
    days = _parse_range_days(range, default_days=30, max_days=365)
    since = datetime.utcnow() - timedelta(days=days)

    with engine.begin() as conn:
        r = conn.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE LOWER(cr.status) = 'pending') AS pending,
                COUNT(*) FILTER (WHERE LOWER(cr.status) = 'processing') AS processing,
                COUNT(*) FILTER (WHERE LOWER(cr.status) = 'sent') AS sent,
                COUNT(*) FILTER (WHERE LOWER(cr.status) = 'delivered') AS delivered,
                COUNT(*) FILTER (WHERE LOWER(cr.status) = 'read') AS read,
                COUNT(*) FILTER (WHERE LOWER(cr.status) = 'replied') AS replied,
                COUNT(*) FILTER (WHERE LOWER(cr.status) = 'failed') AS failed
            FROM campaign_recipients cr
            JOIN campaigns c ON c.id = cr.campaign_id
            WHERE c.created_at >= :since
        """), {"since": since}).mappings().first()

    d = dict(r or {})
    sent = int(d.get("sent") or 0)
    delivered = int(d.get("delivered") or 0)
    read = int(d.get("read") or 0)
    replied = int(d.get("replied") or 0)

    return {
        "range_days": days,
        "since": since,
        "metrics": {
            "pending": int(d.get("pending") or 0),
            "processing": int(d.get("processing") or 0),
            "sent": sent,
            "delivered": delivered,
            "read": read,
            "replied": replied,
            "failed": int(d.get("failed") or 0),
            "delivery_rate_pct": round((delivered / sent) * 100, 2) if sent else 0.0,
            "read_rate_pct": round((read / delivered) * 100, 2) if delivered else 0.0,
            "reply_rate_pct": round((replied / read) * 100, 2) if read else 0.0,
        },
    }


@app.get("/api/dashboard/remarketing")
def dashboard_remarketing():
    with engine.begin() as conn:
        r = conn.execute(text("""
            SELECT
                COUNT(*) AS flows_total,
                COUNT(*) FILTER (WHERE is_active = TRUE) AS active_flows
            FROM remarketing_flows
        """)).mappings().first()

        rs = conn.execute(text("""
            SELECT COUNT(*) AS steps_total
            FROM remarketing_steps
        """)).mappings().first()

    return {
        "flows_total": int((r or {}).get("flows_total") or 0),
        "active_flows": int((r or {}).get("active_flows") or 0),
        "steps_total": int((rs or {}).get("steps_total") or 0),
    }


# =========================================================
# Customers + Segments
# =========================================================

@app.get("/api/customers/segments")
def list_customer_segments(active: str = Query("all", description="all|yes|no")):
    active = (active or "all").strip().lower()
    where_sql = ""
    if active == "yes":
        where_sql = "WHERE is_active = TRUE"
    elif active == "no":
        where_sql = "WHERE is_active = FALSE"

    with engine.begin() as conn:
        rows = conn.execute(text(f"""
            SELECT id, name, rules_json, is_active, created_at, updated_at
            FROM customer_segments
            {where_sql}
            ORDER BY updated_at DESC, id DESC
        """)).mappings().all()

    return {"segments": [dict(r) for r in rows]}


@app.post("/api/customers/segments")
def create_customer_segment(payload: SegmentIn):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO customer_segments (name, rules_json, is_active, created_at, updated_at)
            VALUES (:name, CAST(:rules_json AS jsonb), :is_active, NOW(), NOW())
            RETURNING id, name, rules_json, is_active, created_at, updated_at
        """), {
            "name": name,
            "rules_json": json.dumps(_safe_json_dict(payload.rules_json), ensure_ascii=False),
            "is_active": bool(payload.is_active),
        }).mappings().first()

    return {"segment": dict(row or {})}


@app.patch("/api/customers/segments/{segment_id}")
def update_customer_segment(segment_id: int, payload: SegmentPatch):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="no fields to update")

    sets: List[str] = ["updated_at = NOW()"]
    params: Dict[str, Any] = {"segment_id": int(segment_id)}

    if "name" in data:
        name = str(data.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name cannot be empty")
        sets.append("name = :name")
        params["name"] = name

    if "rules_json" in data:
        sets.append("rules_json = CAST(:rules_json AS jsonb)")
        params["rules_json"] = json.dumps(_safe_json_dict(data.get("rules_json")), ensure_ascii=False)

    if "is_active" in data:
        sets.append("is_active = :is_active")
        params["is_active"] = bool(data.get("is_active"))

    with engine.begin() as conn:
        row = conn.execute(text(f"""
            UPDATE customer_segments
            SET {", ".join(sets)}
            WHERE id = :segment_id
            RETURNING id, name, rules_json, is_active, created_at, updated_at
        """), params).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="segment not found")

    return {"segment": dict(row)}


@app.get("/api/remarketing/filter-options")
def remarketing_filter_options(limit: int = Query(300, ge=20, le=5000)):
    cap = int(limit)

    with engine.begin() as conn:
        intent_rows = conn.execute(
            text(
                """
                SELECT DISTINCT UPPER(TRIM(COALESCE(c.intent_current, ''))) AS value
                FROM conversations c
                WHERE TRIM(COALESCE(c.intent_current, '')) <> ''
                ORDER BY value ASC
                LIMIT :limit
                """
            ),
            {"limit": cap},
        ).mappings().all()

        payment_rows = conn.execute(
            text(
                """
                SELECT DISTINCT LOWER(TRIM(COALESCE(c.payment_status, ''))) AS value
                FROM conversations c
                WHERE TRIM(COALESCE(c.payment_status, '')) <> ''
                ORDER BY value ASC
                LIMIT :limit
                """
            ),
            {"limit": cap},
        ).mappings().all()

        city_rows = conn.execute(
            text(
                """
                SELECT DISTINCT LOWER(TRIM(COALESCE(c.city, ''))) AS value
                FROM conversations c
                WHERE TRIM(COALESCE(c.city, '')) <> ''
                ORDER BY value ASC
                LIMIT :limit
                """
            ),
            {"limit": cap},
        ).mappings().all()

        customer_type_rows = conn.execute(
            text(
                """
                SELECT DISTINCT LOWER(TRIM(COALESCE(c.customer_type, ''))) AS value
                FROM conversations c
                WHERE TRIM(COALESCE(c.customer_type, '')) <> ''
                ORDER BY value ASC
                LIMIT :limit
                """
            ),
            {"limit": cap},
        ).mappings().all()

        tag_rows = conn.execute(
            text(
                """
                SELECT DISTINCT q.tag AS value
                FROM (
                    SELECT TRIM(LOWER(x)) AS tag
                    FROM conversations c
                    CROSS JOIN LATERAL regexp_split_to_table(COALESCE(c.tags, ''), ',') AS x
                    WHERE TRIM(x) <> ''
                    UNION
                    SELECT TRIM(LOWER(COALESCE(l.label_key, ''))) AS tag
                    FROM crm_labels l
                    WHERE TRIM(COALESCE(l.label_key, '')) <> ''
                ) q
                ORDER BY q.tag ASC
                LIMIT :limit
                """
            ),
            {"limit": cap},
        ).mappings().all()

    def _vals(rows: List[Dict[str, Any]]) -> List[str]:
        out: List[str] = []
        seen = set()
        for row in rows:
            token = str((row or {}).get("value") or "").strip()
            if not token:
                continue
            key = token.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(token)
        return out

    return {
        "options": {
            "intent": _vals(intent_rows),
            "tag": _vals(tag_rows),
            "payment_status": _vals(payment_rows),
            "city": _vals(city_rows),
            "customer_type": _vals(customer_type_rows),
            "takeover": ["all", "on", "off"],
        }
    }


@app.get("/api/labels")
def list_labels(
    active: str = Query("all", description="all|yes|no"),
    search: str = Query("", description="Buscar por nombre/key/descripcion"),
    limit: int = Query(300, ge=1, le=2000),
):
    active = (active or "all").strip().lower()
    search = (search or "").strip().lower()

    where: List[str] = []
    params: Dict[str, Any] = {"limit": int(limit)}

    if active == "yes":
        where.append("l.is_active = TRUE")
    elif active == "no":
        where.append("l.is_active = FALSE")

    if search:
        where.append(
            "(LOWER(l.name) LIKE :search OR LOWER(l.label_key) LIKE :search OR LOWER(COALESCE(l.description,'')) LIKE :search)"
        )
        params["search"] = f"%{search}%"

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT
                    l.id,
                    l.label_key,
                    l.name,
                    l.color,
                    l.icon,
                    l.description,
                    l.is_active,
                    l.created_at,
                    l.updated_at,
                    COALESCE(u.usage_count, 0) AS usage_count
                FROM crm_labels l
                LEFT JOIN (
                    SELECT
                        TRIM(LOWER(x)) AS tag_key,
                        COUNT(DISTINCT c.phone) AS usage_count
                    FROM conversations c
                    CROSS JOIN LATERAL regexp_split_to_table(COALESCE(c.tags, ''), ',') AS x
                    WHERE TRIM(x) <> ''
                    GROUP BY TRIM(LOWER(x))
                ) u
                  ON u.tag_key = l.label_key
                {where_sql}
                ORDER BY l.updated_at DESC, l.id DESC
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()

    return {"labels": [dict(r) for r in rows]}


@app.post("/api/labels")
def create_label(payload: LabelIn):
    name = str(payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    label_key = _normalize_label_key(payload.label_key, fallback=name)
    color = _normalize_label_color(payload.color)
    icon = _normalize_label_icon(payload.icon)
    description = str(payload.description or "").strip()

    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT id FROM crm_labels WHERE label_key = :label_key LIMIT 1"),
            {"label_key": label_key},
        ).mappings().first()
        if exists:
            raise HTTPException(status_code=409, detail="label_key already exists")

        row = conn.execute(
            text(
                """
                INSERT INTO crm_labels (
                    label_key, name, color, icon, description, is_active, created_at, updated_at
                )
                VALUES (
                    :label_key, :name, :color, :icon, :description, :is_active, NOW(), NOW()
                )
                RETURNING id, label_key, name, color, icon, description, is_active, created_at, updated_at
                """
            ),
            {
                "label_key": label_key,
                "name": name,
                "color": color,
                "icon": icon,
                "description": description,
                "is_active": bool(payload.is_active),
            },
        ).mappings().first()

    return {"label": dict(row or {})}


@app.patch("/api/labels/{label_id}")
def update_label(label_id: int, payload: LabelPatch):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="no fields to update")

    with engine.begin() as conn:
        current = conn.execute(
            text(
                """
                SELECT id, label_key, name, color, icon, description, is_active
                FROM crm_labels
                WHERE id = :label_id
                LIMIT 1
                """
            ),
            {"label_id": int(label_id)},
        ).mappings().first()
        if not current:
            raise HTTPException(status_code=404, detail="label not found")

        sets: List[str] = ["updated_at = NOW()"]
        params: Dict[str, Any] = {"label_id": int(label_id)}
        old_key = str(current.get("label_key") or "").strip().lower()
        new_key = old_key

        if "name" in data:
            name = str(data.get("name") or "").strip()
            if not name:
                raise HTTPException(status_code=400, detail="name cannot be empty")
            sets.append("name = :name")
            params["name"] = name

        if "label_key" in data:
            proposed_key = _normalize_label_key(str(data.get("label_key") or ""), fallback=str(current.get("name") or "label"))
            check = conn.execute(
                text("SELECT id FROM crm_labels WHERE label_key = :label_key AND id <> :label_id LIMIT 1"),
                {"label_key": proposed_key, "label_id": int(label_id)},
            ).mappings().first()
            if check:
                raise HTTPException(status_code=409, detail="label_key already exists")
            sets.append("label_key = :label_key")
            params["label_key"] = proposed_key
            new_key = proposed_key

        if "color" in data:
            sets.append("color = :color")
            params["color"] = _normalize_label_color(data.get("color"))

        if "icon" in data:
            sets.append("icon = :icon")
            params["icon"] = _normalize_label_icon(data.get("icon"))

        if "description" in data:
            sets.append("description = :description")
            params["description"] = str(data.get("description") or "").strip()

        if "is_active" in data:
            sets.append("is_active = :is_active")
            params["is_active"] = bool(data.get("is_active"))

        row = conn.execute(
            text(
                f"""
                UPDATE crm_labels
                SET {", ".join(sets)}
                WHERE id = :label_id
                RETURNING id, label_key, name, color, icon, description, is_active, created_at, updated_at
                """
            ),
            params,
        ).mappings().first()

        renamed_on = 0
        if old_key and new_key and old_key != new_key:
            renamed_on = _replace_tag_key_everywhere(conn, old_key, new_key)

    return {"label": dict(row or {}), "renamed_on_conversations": int(renamed_on)}


@app.delete("/api/labels/{label_id}")
def delete_label(label_id: int, cleanup_tags: bool = Query(False, description="Si true, remueve el tag de conversaciones")):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, label_key, name
                FROM crm_labels
                WHERE id = :label_id
                LIMIT 1
                """
            ),
            {"label_id": int(label_id)},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="label not found")

        cleaned = 0
        if cleanup_tags:
            cleaned = _remove_tag_key_everywhere(conn, str(row.get("label_key") or ""))

        conn.execute(
            text("DELETE FROM crm_labels WHERE id = :label_id"),
            {"label_id": int(label_id)},
        )

    return {
        "ok": True,
        "deleted": {"id": int(row.get("id") or 0), "label_key": str(row.get("label_key") or ""), "name": str(row.get("name") or "")},
        "cleanup_tags": bool(cleanup_tags),
        "conversations_cleaned": int(cleaned),
    }


@app.get("/api/customers")
def list_customers(
    search: str = Query("", description="Buscar por telefono/nombre/texto"),
    tag: str = Query("", description="Tag contiene"),
    intent: str = Query("", description="Intent exacto"),
    payment_status: str = Query("", description="payment_status exacto"),
    takeover: str = Query("all", description="all|on|off"),
    unread: str = Query("all", description="all|yes|no"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    term = (search or "").strip().lower()
    tag = (tag or "").strip().lower()
    intent = (intent or "").strip().upper()
    payment_status = (payment_status or "").strip().lower()
    takeover = (takeover or "all").strip().lower()
    unread = (unread or "all").strip().lower()

    where: List[str] = []
    params: Dict[str, Any] = {"limit": page_size, "offset": (page - 1) * page_size}

    if term:
        where.append("""
            (
                LOWER(c.phone) LIKE :term
                OR LOWER(COALESCE(c.first_name,'') || ' ' || COALESCE(c.last_name,'')) LIKE :term
                OR EXISTS (
                    SELECT 1
                    FROM messages mx
                    WHERE mx.phone = c.phone
                      AND LOWER(COALESCE(mx.text, '')) LIKE :term
                )
            )
        """)
        params["term"] = f"%{term}%"

    if tag:
        where.append("LOWER(COALESCE(c.tags,'')) LIKE :tag")
        params["tag"] = f"%{tag}%"

    if intent:
        where.append("UPPER(COALESCE(c.intent_current,'')) = :intent")
        params["intent"] = intent

    if payment_status:
        where.append("LOWER(COALESCE(c.payment_status,'')) = :payment_status")
        params["payment_status"] = payment_status

    if takeover == "on":
        where.append("c.takeover = TRUE")
    elif takeover == "off":
        where.append("c.takeover = FALSE")

    unread_sql = """
        EXISTS (
            SELECT 1
            FROM messages mi
            WHERE mi.phone = c.phone
              AND mi.direction = 'in'
              AND mi.created_at > COALESCE(c.last_read_at, TIMESTAMP 'epoch')
        )
    """
    if unread == "yes":
        where.append(unread_sql)
    elif unread == "no":
        where.append(f"NOT ({unread_sql})")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    with engine.begin() as conn:
        rows = conn.execute(text(f"""
            SELECT
                c.phone,
                c.takeover,
                c.updated_at,
                c.first_name,
                c.last_name,
                c.city,
                c.customer_type,
                c.interests,
                c.tags,
                c.notes,
                c.intent_current,
                c.intent_stage,
                c.payment_status,
                c.payment_reference,
                m.text AS last_text,
                m.created_at AS last_message_at,
                (
                    SELECT COUNT(*)
                    FROM messages mm
                    WHERE mm.phone = c.phone
                ) AS messages_total,
                {unread_sql} AS has_unread
            FROM conversations c
            LEFT JOIN LATERAL (
                SELECT text, created_at
                FROM messages
                WHERE phone = c.phone
                ORDER BY created_at DESC
                LIMIT 1
            ) m ON TRUE
            {where_sql}
            ORDER BY c.updated_at DESC
            LIMIT :limit OFFSET :offset
        """), params).mappings().all()

        total_row = conn.execute(text(f"""
            SELECT COUNT(*) AS total
            FROM conversations c
            {where_sql}
        """), params).mappings().first()

    return {
        "page": page,
        "page_size": page_size,
        "total": int((total_row or {}).get("total") or 0),
        "customers": [dict(r) for r in rows],
    }


@app.get("/api/customers/{phone}")
def get_customer(phone: str):
    phone = (phone or "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="phone required")

    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT
                c.phone,
                c.takeover,
                c.updated_at,
                c.first_name,
                c.last_name,
                c.city,
                c.customer_type,
                c.interests,
                c.tags,
                c.notes,
                c.intent_current,
                c.intent_stage,
                c.payment_status,
                c.payment_reference,
                c.payment_amount,
                c.payment_currency,
                COALESCE(c.crm_meta, '{}'::jsonb) AS crm_meta,
                (
                    SELECT COUNT(*)
                    FROM messages m
                    WHERE m.phone = c.phone
                ) AS messages_total
            FROM conversations c
            WHERE c.phone = :phone
            LIMIT 1
        """), {"phone": phone}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="customer not found")

    return {"customer": dict(row)}


@app.patch("/api/customers/{phone}")
def patch_customer(phone: str, payload: CustomerPatch):
    phone = (phone or "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="phone required")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return get_customer(phone)

    allowed = {
        "first_name",
        "last_name",
        "city",
        "customer_type",
        "interests",
        "tags",
        "notes",
        "payment_status",
        "payment_reference",
    }
    fields = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        raise HTTPException(status_code=400, detail="no valid fields to update")

    set_parts = ["updated_at = :updated_at"]
    params: Dict[str, Any] = {"phone": phone, "updated_at": datetime.utcnow()}

    for k, v in fields.items():
        set_parts.append(f"{k} = :{k}")
        params[k] = "" if v is None else str(v)

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO conversations (phone, updated_at)
            VALUES (:phone, :updated_at)
            ON CONFLICT (phone) DO NOTHING
        """), {"phone": phone, "updated_at": params["updated_at"]})

        conn.execute(text(f"""
            UPDATE conversations
            SET {", ".join(set_parts)}
            WHERE phone = :phone
        """), params)

    return get_customer(phone)


@app.get("/api/customers/{phone}/context")
def get_customer_context(
    phone: str,
    history_limit: int = Query(30, ge=5, le=120),
    max_chars: int = Query(6000, ge=300, le=12000),
):
    p = (phone or "").strip()
    if not p:
        raise HTTPException(status_code=400, detail="phone required")

    meta = build_ai_meta(p, "", history_limit=history_limit)
    context = str(meta.get("context") or "")
    if max_chars > 0 and len(context) > max_chars:
        context = context[:max_chars].rstrip() + "..."

    return {
        "phone": p,
        "history_limit": int(history_limit),
        "context_chars": len(context),
        "flags": meta.get("flags") if isinstance(meta.get("flags"), dict) else {},
        "crm": meta.get("crm") if isinstance(meta.get("crm"), dict) else {},
        "context": context,
    }


@app.get("/api/customers/{phone}/intent-analysis")
def customer_intent_analysis(
    phone: str,
    limit: int = Query(30, ge=5, le=120),
):
    p = (phone or "").strip()
    if not p:
        raise HTTPException(status_code=400, detail="phone required")

    with engine.begin() as conn:
        convo = conn.execute(
            text(
                """
                SELECT
                    COALESCE(ai_state, '') AS ai_state,
                    COALESCE(first_name, '') AS first_name,
                    COALESCE(last_name, '') AS last_name,
                    COALESCE(city, '') AS city,
                    COALESCE(customer_type, '') AS customer_type,
                    COALESCE(tags, '') AS tags,
                    COALESCE(payment_status, '') AS payment_status
                FROM conversations
                WHERE phone = :phone
                LIMIT 1
                """
            ),
            {"phone": p},
        ).mappings().first() or {}

        rows = conn.execute(
            text(
                """
                SELECT
                    id,
                    phone,
                    direction,
                    msg_type,
                    COALESCE(text, '') AS text,
                    COALESCE(extracted_text, '') AS extracted_text,
                    created_at
                FROM messages
                WHERE phone = :phone
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"phone": p, "limit": int(limit)},
        ).mappings().all()

    messages = [dict(r) for r in rows]
    messages.reverse()

    crm_snapshot = {
        "first_name": str(convo.get("first_name") or ""),
        "last_name": str(convo.get("last_name") or ""),
        "city": str(convo.get("city") or ""),
        "customer_type": str(convo.get("customer_type") or ""),
        "tags": str(convo.get("tags") or ""),
        "payment_status": str(convo.get("payment_status") or ""),
    }
    ai_state = str(convo.get("ai_state") or "")

    intent_counter: Counter[str] = Counter()
    term_counter: Counter[str] = Counter()
    query_counter: Counter[str] = Counter()
    timeline: List[Dict[str, Any]] = []

    incoming_total = 0
    perfume_related_total = 0

    for row in messages:
        direction = str(row.get("direction") or "").strip().lower()
        msg_type = str(row.get("msg_type") or "text").strip().lower()
        text_value = str(row.get("text") or "")
        extracted = str(row.get("extracted_text") or "")

        event: Dict[str, Any] = {
            "id": int(row.get("id") or 0),
            "created_at": row.get("created_at"),
            "direction": direction,
            "msg_type": msg_type,
            "text": text_value,
        }

        if direction == "in":
            incoming_total += 1
            intent = detect_intent(
                user_text=text_value,
                msg_type=msg_type,
                state=ai_state,
                extracted_text=extracted,
                crm_snapshot=crm_snapshot,
            )
            normalized_intent = str(intent.intent or "").strip().upper()
            confidence = float(intent.confidence or 0)
            payload = intent.payload if isinstance(intent.payload, dict) else {}
            query = str(payload.get("query") or "").strip()
            perfume_related = _is_perfume_related_intent(normalized_intent)

            intent_counter[normalized_intent] += 1
            if perfume_related:
                perfume_related_total += 1
            if query:
                query_counter[query] += 1

            for term in _extract_perfume_terms(f"{text_value} {extracted} {query}"):
                term_counter[term] += 1

            event.update(
                {
                    "intent": normalized_intent or "UNKNOWN",
                    "confidence": round(confidence, 3),
                    "perfume_related": perfume_related,
                    "query": query,
                }
            )
        else:
            for term in _extract_perfume_terms(text_value):
                term_counter[term] += 1

        timeline.append(event)

    top_intents = [
        {"intent": k, "count": int(v)}
        for k, v in intent_counter.most_common(8)
    ]
    top_terms = [
        {"term": k, "count": int(v)}
        for k, v in term_counter.most_common(12)
    ]
    top_queries = [
        {"query": k, "count": int(v)}
        for k, v in query_counter.most_common(8)
    ]

    perfume_ratio = (perfume_related_total / incoming_total) if incoming_total else 0.0
    signals = []
    if perfume_ratio >= 0.7:
        signals.append("interes_alto_perfumeria")
    if intent_counter.get("BUY_FLOW", 0) > 0:
        signals.append("senal_compra")
    if intent_counter.get("PRICE_STOCK", 0) > 0:
        signals.append("consulta_precio_stock")
    if intent_counter.get("UNKNOWN", 0) >= max(3, incoming_total // 2):
        signals.append("intencion_ambigua")

    return {
        "phone": p,
        "window_messages": len(messages),
        "incoming_messages_analyzed": int(incoming_total),
        "perfume_related_messages": int(perfume_related_total),
        "perfume_interest_ratio": round(perfume_ratio, 4),
        "top_intents": top_intents,
        "top_terms": top_terms,
        "top_queries": top_queries,
        "signals": signals,
        "timeline": timeline,
    }


# =========================================================
# Templates
# =========================================================

@app.get("/api/templates")
def list_templates(
    status: str = Query("all", description="all|draft|approved|archived"),
    channel: str = Query("whatsapp", description="whatsapp|facebook|instagram|tiktok|all"),
    category: str = Query("", description="Categoria"),
    search: str = Query("", description="Buscar por nombre/body"),
):
    status = (status or "all").strip().lower()
    channel = (channel or "whatsapp").strip().lower()
    category = (category or "").strip().lower()
    search = (search or "").strip().lower()

    where: List[str] = []
    params: Dict[str, Any] = {}

    if status != "all":
        where.append("LOWER(t.status) = :status")
        params["status"] = status

    if channel != "all":
        where.append("LOWER(COALESCE(t.channel, 'whatsapp')) = :channel")
        params["channel"] = _normalize_channel(channel, default="whatsapp")

    if category:
        where.append("LOWER(t.category) = :category")
        params["category"] = category

    if search:
        where.append("(LOWER(t.name) LIKE :search OR LOWER(t.body) LIKE :search)")
        params["search"] = f"%{search}%"

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    with engine.begin() as conn:
        rows = conn.execute(text(f"""
            SELECT
                t.id, t.name, t.category, t.channel, t.body, t.variables_json, t.blocks_json, t.params_json, t.render_mode, t.status, t.created_at, t.updated_at
            FROM message_templates t
            {where_sql}
            ORDER BY t.updated_at DESC, t.id DESC
        """), params).mappings().all()

    return {"templates": [dict(r) for r in rows]}


@app.get("/api/templates/params/catalog")
def templates_params_catalog():
    return {"params": _template_params_catalog()}


@app.post("/api/templates")
def create_template(payload: TemplateIn):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    status = _normalize_status(
        payload.status,
        allowed={"draft", "approved", "archived"},
        default="draft",
    )

    vars_clean = []
    seen = set()
    for raw in payload.variables_json or []:
        key = str(raw or "").strip()
        if not key:
            continue
        key_low = key.lower()
        if key_low in seen:
            continue
        seen.add(key_low)
        vars_clean.append(key)

    blocks_clean = _normalize_template_blocks(payload.blocks_json, body_fallback=payload.body or "")

    body = str(payload.body or "").strip()
    if not body and blocks_clean:
        first_text = next((b.get("text") for b in blocks_clean if b.get("kind") == "text" and b.get("text")), "")
        body = str(first_text or "").strip()

    render_mode = (payload.render_mode or "chat").strip().lower()
    if render_mode not in ("chat", "plain"):
        render_mode = "chat"

    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO message_templates (
                name, category, channel, body, variables_json, blocks_json, params_json, render_mode, status, created_at, updated_at
            )
            VALUES (
                :name, :category, :channel, :body, CAST(:variables_json AS jsonb), CAST(:blocks_json AS jsonb), CAST(:params_json AS jsonb), :render_mode, :status, NOW(), NOW()
            )
            RETURNING id, name, category, channel, body, variables_json, blocks_json, params_json, render_mode, status, created_at, updated_at
        """), {
            "name": name,
            "category": (payload.category or "general").strip().lower() or "general",
            "channel": _normalize_channel(payload.channel, default="whatsapp"),
            "body": body,
            "variables_json": json.dumps(vars_clean, ensure_ascii=False),
            "blocks_json": json.dumps(blocks_clean, ensure_ascii=False),
            "params_json": json.dumps(_safe_json_dict(payload.params_json), ensure_ascii=False),
            "render_mode": render_mode,
            "status": status,
        }).mappings().first()

    return {"template": dict(row or {})}


@app.patch("/api/templates/{template_id}")
def update_template(template_id: int, payload: TemplatePatch):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="no fields to update")

    sets: List[str] = ["updated_at = NOW()"]
    params: Dict[str, Any] = {"template_id": int(template_id)}

    if "name" in data:
        name = str(data.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name cannot be empty")
        sets.append("name = :name")
        params["name"] = name

    if "category" in data:
        sets.append("category = :category")
        params["category"] = (str(data.get("category") or "").strip().lower() or "general")

    if "channel" in data:
        sets.append("channel = :channel")
        params["channel"] = _normalize_channel(str(data.get("channel") or ""), default="whatsapp")

    if "body" in data:
        sets.append("body = :body")
        params["body"] = str(data.get("body") or "")

    if "variables_json" in data:
        vars_clean = []
        seen = set()
        for raw in (data.get("variables_json") or []):
            key = str(raw or "").strip()
            if not key:
                continue
            kl = key.lower()
            if kl in seen:
                continue
            seen.add(kl)
            vars_clean.append(key)
        sets.append("variables_json = CAST(:variables_json AS jsonb)")
        params["variables_json"] = json.dumps(vars_clean, ensure_ascii=False)

    if "blocks_json" in data:
        fallback_body = str(data.get("body") or "")
        blocks_clean = _normalize_template_blocks(data.get("blocks_json"), body_fallback=fallback_body)
        sets.append("blocks_json = CAST(:blocks_json AS jsonb)")
        params["blocks_json"] = json.dumps(blocks_clean, ensure_ascii=False)

        if "body" not in data:
            first_text = next((b.get("text") for b in blocks_clean if b.get("kind") == "text" and b.get("text")), "")
            if first_text:
                sets.append("body = :body_from_blocks")
                params["body_from_blocks"] = str(first_text)

    if "params_json" in data:
        sets.append("params_json = CAST(:params_json AS jsonb)")
        params["params_json"] = json.dumps(_safe_json_dict(data.get("params_json")), ensure_ascii=False)

    if "render_mode" in data:
        mode = (str(data.get("render_mode") or "")).strip().lower()
        if mode not in ("chat", "plain"):
            mode = "chat"
        sets.append("render_mode = :render_mode")
        params["render_mode"] = mode

    if "status" in data:
        sets.append("status = :status")
        params["status"] = _normalize_status(
            str(data.get("status") or ""),
            allowed={"draft", "approved", "archived"},
            default="draft",
        )

    with engine.begin() as conn:
        row = conn.execute(text(f"""
            UPDATE message_templates
            SET {", ".join(sets)}
            WHERE id = :template_id
            RETURNING id, name, category, channel, body, variables_json, blocks_json, params_json, render_mode, status, created_at, updated_at
        """), params).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="template not found")

    return {"template": dict(row)}


@app.delete("/api/templates/{template_id}")
def delete_template(template_id: int):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, name
                FROM message_templates
                WHERE id = :template_id
                LIMIT 1
                """
            ),
            {"template_id": int(template_id)},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="template not found")

        usage = conn.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM campaigns c WHERE c.template_id = :template_id) AS campaigns_count,
                    (SELECT COUNT(*) FROM remarketing_steps s WHERE s.template_id = :template_id) AS remarketing_steps_count,
                    (
                        SELECT COUNT(*)
                        FROM trigger_scheduled_messages sm
                        WHERE sm.template_id = :template_id
                          AND LOWER(sm.status) IN ('pending', 'processing')
                    ) AS trigger_scheduled_pending_count
                """
            ),
            {"template_id": int(template_id)},
        ).mappings().first()

        conn.execute(
            text(
                """
                DELETE FROM message_templates
                WHERE id = :template_id
                """
            ),
            {"template_id": int(template_id)},
        )

    return {
        "ok": True,
        "deleted": {"id": int(row.get("id") or 0), "name": str(row.get("name") or "").strip()},
        "detached": {
            "campaigns": int((usage or {}).get("campaigns_count") or 0),
            "remarketing_steps": int((usage or {}).get("remarketing_steps_count") or 0),
            "trigger_scheduled_pending": int((usage or {}).get("trigger_scheduled_pending_count") or 0),
        },
    }


@app.post("/api/templates/{template_id}/copy")
def copy_template_to_channel(template_id: int, payload: ChannelCopyIn):
    target_channel = _normalize_channel(payload.target_channel, default="")
    if not target_channel:
        raise HTTPException(status_code=400, detail="target_channel invalid")

    suffix = str(payload.name_suffix or "").strip()

    with engine.begin() as conn:
        src = conn.execute(
            text(
                """
                SELECT
                    id, name, category, channel, body, variables_json, blocks_json,
                    params_json, render_mode, status
                FROM message_templates
                WHERE id = :template_id
                LIMIT 1
                """
            ),
            {"template_id": int(template_id)},
        ).mappings().first()
        if not src:
            raise HTTPException(status_code=404, detail="template not found")

        src_channel = _normalize_channel(str(src.get("channel") or "whatsapp"), default="whatsapp")
        if src_channel == target_channel:
            raise HTTPException(status_code=409, detail="template already in target channel")

        base_name = str(src.get("name") or "").strip() or f"Template {int(template_id)}"
        new_name = f"{base_name} {suffix}".strip() if suffix else f"{base_name} [{target_channel}]"

        new_row = conn.execute(
            text(
                """
                INSERT INTO message_templates (
                    name,
                    category,
                    channel,
                    body,
                    variables_json,
                    blocks_json,
                    params_json,
                    render_mode,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (
                    :name,
                    :category,
                    :channel,
                    :body,
                    CAST(:variables_json AS jsonb),
                    CAST(:blocks_json AS jsonb),
                    CAST(:params_json AS jsonb),
                    :render_mode,
                    :status,
                    NOW(),
                    NOW()
                )
                RETURNING
                    id, name, category, channel, body, variables_json, blocks_json,
                    params_json, render_mode, status, created_at, updated_at
                """
            ),
            {
                "name": new_name[:180],
                "category": str(src.get("category") or "general").strip().lower() or "general",
                "channel": target_channel,
                "body": str(src.get("body") or ""),
                "variables_json": json.dumps(src.get("variables_json") or [], ensure_ascii=False),
                "blocks_json": json.dumps(src.get("blocks_json") or [], ensure_ascii=False),
                "params_json": json.dumps(_safe_json_dict(src.get("params_json")), ensure_ascii=False),
                "render_mode": (str(src.get("render_mode") or "chat").strip().lower() or "chat"),
                "status": _normalize_status(
                    str(src.get("status") or ""),
                    allowed={"draft", "approved", "archived"},
                    default="draft",
                ),
            },
        ).mappings().first()

    return {"ok": True, "source_template_id": int(template_id), "template": dict(new_row or {})}


@app.post("/api/templates/{template_id}/preview")
def preview_template(template_id: int, payload: TemplatePreviewIn):
    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT id, name, body, variables_json, blocks_json, params_json, render_mode
            FROM message_templates
            WHERE id = :template_id
            LIMIT 1
        """), {"template_id": int(template_id)}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="template not found")

    template = dict(row)
    params_json = _safe_json_dict(template.get("params_json"))
    user_vars = payload.variables or {}

    resolved_vars: Dict[str, Any] = {}
    for k, v in params_json.items():
        resolved_vars[str(k)] = v
    for k, v in user_vars.items():
        resolved_vars[str(k)] = v

    blocks = _normalize_template_blocks(template.get("blocks_json"), body_fallback=template.get("body") or "")
    rendered_blocks: List[Dict[str, Any]] = []
    missing_params: List[str] = []

    for b in blocks:
        kind = str(b.get("kind") or "text").lower()
        delay_ms = int(b.get("delay_ms") or 0)
        if kind in ("image", "video", "audio"):
            media_url_key = "image_url" if kind == "image" else ("video_url" if kind == "video" else "audio_url")
            media_url = str(b.get(media_url_key) or b.get("media_url") or b.get("url") or "")
            block_out = {
                "kind": kind,
                "media_id": str(b.get("media_id") or ""),
                media_url_key: media_url,
                "delay_ms": delay_ms,
            }
            if kind in ("image", "video"):
                caption = _render_template(str(b.get("caption") or ""), resolved_vars)
                block_out["caption"] = caption
                missing_params.extend(_collect_missing_params(str(b.get("caption") or ""), resolved_vars))
            rendered_blocks.append(block_out)
            continue

        text_val = _render_template(str(b.get("text") or ""), resolved_vars)
        rendered_blocks.append({"kind": "text", "text": text_val, "delay_ms": delay_ms})
        missing_params.extend(_collect_missing_params(str(b.get("text") or ""), resolved_vars))

    missing_unique: List[str] = []
    for m in missing_params:
        if m not in missing_unique:
            missing_unique.append(m)

    preview_text = "\n\n".join(
        [x.get("text") or x.get("caption") or "" for x in rendered_blocks if (x.get("text") or x.get("caption"))]
    ).strip()

    return {
        "preview": preview_text,
        "messages_rendered": rendered_blocks,
        "resolved_params": resolved_vars,
        "missing_params": missing_unique,
        "template": template,
    }


@app.post("/api/templates/{template_id}/render")
def render_template_with_context(template_id: int, payload: TemplateRenderIn):
    with engine.begin() as conn:
        tpl = conn.execute(text("""
            SELECT id, name, body, variables_json, blocks_json, params_json, render_mode
            FROM message_templates
            WHERE id = :template_id
            LIMIT 1
        """), {"template_id": int(template_id)}).mappings().first()

        if not tpl:
            raise HTTPException(status_code=404, detail="template not found")

        template = dict(tpl)
        resolved: Dict[str, Any] = {}
        for k, v in _safe_json_dict(template.get("params_json")).items():
            resolved[str(k)] = v

        phone = (payload.phone or "").strip()
        if phone:
            conv = conn.execute(text("""
                SELECT
                    c.phone,
                    c.first_name,
                    c.last_name,
                    c.city,
                    c.customer_type,
                    c.tags,
                    c.payment_status,
                    COALESCE(c.crm_meta->>'country', 'CO') AS country,
                    (
                        SELECT MIN(m0.created_at)
                        FROM messages m0
                        WHERE m0.phone = c.phone
                    ) AS first_message_date,
                    (
                        SELECT MAX(m1.created_at)
                        FROM messages m1
                        WHERE m1.phone = c.phone
                    ) AS last_message_date
                FROM conversations c
                WHERE c.phone = :phone
                LIMIT 1
            """), {"phone": phone}).mappings().first()

            c = dict(conv or {})
            first_name = str(c.get("first_name") or "").strip()
            last_name = str(c.get("last_name") or "").strip()
            full_name = f"{first_name} {last_name}".strip()
            resolved.update(
                {
                    "nombre": full_name or phone,
                    "customer_name": full_name or phone,
                    "customer_phone": phone,
                    "phone": phone,
                    "city": str(c.get("city") or "").strip(),
                    "customer_type": str(c.get("customer_type") or "").strip(),
                    "customer_tag": str(c.get("tags") or "").strip(),
                    "payment_status": str(c.get("payment_status") or "").strip(),
                    "customer_country": str(c.get("country") or "CO").strip(),
                    "first_message_date": str(c.get("first_message_date") or "").strip(),
                    "last_message_date": str(c.get("last_message_date") or "").strip(),
                }
            )

        if payload.campaign_id:
            camp = conn.execute(text("""
                SELECT id, name, objective
                FROM campaigns
                WHERE id = :campaign_id
                LIMIT 1
            """), {"campaign_id": int(payload.campaign_id)}).mappings().first()
            if camp:
                resolved["campaign_name"] = str(camp.get("name") or "").strip()
                resolved["objective"] = str(camp.get("objective") or "").strip()

    resolved.update(
        {
            "business_name": str(os.getenv("BUSINESS_NAME", "Verane")).strip(),
            "business_phone": str(os.getenv("BUSINESS_PHONE", "")).strip(),
            "business_email": str(os.getenv("BUSINESS_EMAIL", "")).strip(),
            "assistant_name": str(os.getenv("ASSISTANT_NAME", "Asistente Verane")).strip(),
            "assistant_phone": str(os.getenv("ASSISTANT_PHONE", "")).strip(),
        }
    )

    for k, v in (payload.overrides or {}).items():
        resolved[str(k)] = v

    blocks = _normalize_template_blocks(template.get("blocks_json"), body_fallback=template.get("body") or "")
    rendered_blocks: List[Dict[str, Any]] = []
    missing_params: List[str] = []

    for b in blocks:
        kind = str(b.get("kind") or "text").lower()
        delay_ms = int(b.get("delay_ms") or 0)
        if kind in ("image", "video", "audio"):
            media_url_key = "image_url" if kind == "image" else ("video_url" if kind == "video" else "audio_url")
            media_url = str(b.get(media_url_key) or b.get("media_url") or b.get("url") or "")
            block_out = {
                "kind": kind,
                "media_id": str(b.get("media_id") or ""),
                media_url_key: media_url,
                "delay_ms": delay_ms,
            }
            if kind in ("image", "video"):
                caption = _render_template(str(b.get("caption") or ""), resolved)
                block_out["caption"] = caption
                missing_params.extend(_collect_missing_params(str(b.get("caption") or ""), resolved))
            rendered_blocks.append(block_out)
            continue

        txt = _render_template(str(b.get("text") or ""), resolved)
        rendered_blocks.append({"kind": "text", "text": txt, "delay_ms": delay_ms})
        missing_params.extend(_collect_missing_params(str(b.get("text") or ""), resolved))

    missing_unique: List[str] = []
    for m in missing_params:
        if m not in missing_unique:
            missing_unique.append(m)

    return {
        "template_id": int(template_id),
        "messages_rendered": rendered_blocks,
        "resolved_params": resolved,
        "missing_params": missing_unique,
    }


# =========================================================
# Campaigns
# =========================================================

@app.get("/api/campaigns")
def list_campaigns(
    status: str = Query("all", description="all|draft|scheduled|running|paused|completed|archived"),
    channel: str = Query("all", description="whatsapp|facebook|instagram|tiktok|all"),
):
    status = (status or "all").strip().lower()
    channel = (channel or "all").strip().lower()
    params: Dict[str, Any] = {}
    where: List[str] = []
    if status != "all":
        where.append("LOWER(c.status) = :status")
        params["status"] = status
    if channel != "all":
        where.append("LOWER(COALESCE(c.channel, 'whatsapp')) = :channel")
        params["channel"] = _normalize_channel(channel, default="whatsapp")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    with engine.begin() as conn:
        rows = conn.execute(text(f"""
            SELECT
                c.id, c.name, c.objective, c.segment_id, c.template_id,
                c.status, c.scheduled_at, c.launched_at, c.channel,
                c.created_at, c.updated_at,
                s.name AS segment_name,
                t.name AS template_name
            FROM campaigns c
            LEFT JOIN customer_segments s ON s.id = c.segment_id
            LEFT JOIN message_templates t ON t.id = c.template_id
            {where_sql}
            ORDER BY c.updated_at DESC, c.id DESC
        """), params).mappings().all()

    return {"campaigns": [dict(r) for r in rows]}


@app.post("/api/campaigns")
def create_campaign(payload: CampaignIn):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    status = _normalize_status(
        payload.status,
        allowed={"draft", "scheduled", "running", "paused", "completed", "archived"},
        default="draft",
    )
    channel = _normalize_channel(payload.channel, default="whatsapp")

    with engine.begin() as conn:
        if payload.template_id:
            tpl = conn.execute(
                text(
                    """
                    SELECT channel
                    FROM message_templates
                    WHERE id = :template_id
                    LIMIT 1
                    """
                ),
                {"template_id": int(payload.template_id)},
            ).mappings().first()
            if not tpl:
                raise HTTPException(status_code=404, detail="template not found")
            tpl_channel = _normalize_channel(str(tpl.get("channel") or "whatsapp"), default="whatsapp")
            if tpl_channel != channel:
                raise HTTPException(
                    status_code=400,
                    detail=f"template channel mismatch: template={tpl_channel}, campaign={channel}",
                )

        row = conn.execute(text("""
            INSERT INTO campaigns (
                name, objective, segment_id, template_id, status, scheduled_at, channel, created_at, updated_at
            )
            VALUES (
                :name, :objective, :segment_id, :template_id, :status, :scheduled_at, :channel, NOW(), NOW()
            )
            RETURNING
                id, name, objective, segment_id, template_id, status, scheduled_at, launched_at, channel, created_at, updated_at
        """), {
            "name": name,
            "objective": payload.objective or "",
            "segment_id": payload.segment_id,
            "template_id": payload.template_id,
            "status": status,
            "scheduled_at": payload.scheduled_at,
            "channel": channel,
        }).mappings().first()

    return {"campaign": dict(row or {})}


@app.patch("/api/campaigns/{campaign_id}")
def update_campaign(campaign_id: int, payload: CampaignPatch):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="no fields to update")

    sets: List[str] = ["updated_at = NOW()"]
    params: Dict[str, Any] = {"campaign_id": int(campaign_id)}

    if "name" in data:
        name = str(data.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name cannot be empty")
        sets.append("name = :name")
        params["name"] = name

    if "objective" in data:
        sets.append("objective = :objective")
        params["objective"] = str(data.get("objective") or "")

    if "segment_id" in data:
        sets.append("segment_id = :segment_id")
        params["segment_id"] = data.get("segment_id")

    if "template_id" in data:
        sets.append("template_id = :template_id")
        params["template_id"] = data.get("template_id")

    if "status" in data:
        sets.append("status = :status")
        params["status"] = _normalize_status(
            str(data.get("status") or ""),
            allowed={"draft", "scheduled", "running", "paused", "completed", "archived"},
            default="draft",
        )

    if "scheduled_at" in data:
        sets.append("scheduled_at = :scheduled_at")
        params["scheduled_at"] = data.get("scheduled_at")

    with engine.begin() as conn:
        current = conn.execute(
            text(
                """
                SELECT id, channel, template_id
                FROM campaigns
                WHERE id = :campaign_id
                LIMIT 1
                """
            ),
            {"campaign_id": int(campaign_id)},
        ).mappings().first()
        if not current:
            raise HTTPException(status_code=404, detail="campaign not found")

        next_channel = _normalize_channel(str(current.get("channel") or "whatsapp"), default="whatsapp")
        if "channel" in data:
            next_channel = _normalize_channel(str(data.get("channel") or ""), default="whatsapp")
            sets.append("channel = :channel")
            params["channel"] = next_channel

        template_id_for_validation = data.get("template_id", current.get("template_id"))
        if template_id_for_validation:
            tpl = conn.execute(
                text(
                    """
                    SELECT channel
                    FROM message_templates
                    WHERE id = :template_id
                    LIMIT 1
                    """
                ),
                {"template_id": int(template_id_for_validation)},
            ).mappings().first()
            if not tpl:
                raise HTTPException(status_code=404, detail="template not found")
            tpl_channel = _normalize_channel(str(tpl.get("channel") or "whatsapp"), default="whatsapp")
            if tpl_channel != next_channel:
                raise HTTPException(
                    status_code=400,
                    detail=f"template channel mismatch: template={tpl_channel}, campaign={next_channel}",
                )

        row = conn.execute(text(f"""
            UPDATE campaigns
            SET {", ".join(sets)}
            WHERE id = :campaign_id
            RETURNING
                id, name, objective, segment_id, template_id, status, scheduled_at, launched_at, channel, created_at, updated_at
        """), params).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="campaign not found")

    return {"campaign": dict(row)}


@app.delete("/api/campaigns/{campaign_id}")
def delete_campaign(campaign_id: int):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, name
                FROM campaigns
                WHERE id = :campaign_id
                LIMIT 1
                """
            ),
            {"campaign_id": int(campaign_id)},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="campaign not found")

        stats = conn.execute(
            text(
                """
                SELECT COUNT(*) AS recipients_count
                FROM campaign_recipients
                WHERE campaign_id = :campaign_id
                """
            ),
            {"campaign_id": int(campaign_id)},
        ).mappings().first()

        conn.execute(
            text(
                """
                DELETE FROM campaigns
                WHERE id = :campaign_id
                """
            ),
            {"campaign_id": int(campaign_id)},
        )

    return {
        "ok": True,
        "deleted": {"id": int(row.get("id") or 0), "name": str(row.get("name") or "").strip()},
        "cascade": {"campaign_recipients": int((stats or {}).get("recipients_count") or 0)},
    }


@app.post("/api/campaigns/{campaign_id}/launch")
def launch_campaign(campaign_id: int, max_recipients: int = Query(300, ge=1, le=5000)):
    now = datetime.utcnow()
    with engine.begin() as conn:
        campaign = conn.execute(text("""
            SELECT id, segment_id, scheduled_at, channel
            FROM campaigns
            WHERE id = :campaign_id
            LIMIT 1
        """), {"campaign_id": int(campaign_id)}).mappings().first()

        if not campaign:
            raise HTTPException(status_code=404, detail="campaign not found")
        if _normalize_channel(str(campaign.get("channel") or "whatsapp"), default="whatsapp") != "whatsapp":
            raise HTTPException(status_code=409, detail="channel_not_supported_for_launch_yet")

        rules: Dict[str, Any] = {}
        if campaign.get("segment_id"):
            s = conn.execute(text("""
                SELECT rules_json
                FROM customer_segments
                WHERE id = :segment_id
                LIMIT 1
            """), {"segment_id": int(campaign.get("segment_id"))}).mappings().first()
            rules = _safe_json_dict((s or {}).get("rules_json"))

        where_sql, seg_params = _segment_filter_sql(rules, prefix="seg")
        seg_params["campaign_id"] = int(campaign_id)
        seg_params["limit"] = int(max_recipients)

        conn.execute(text(f"""
            WITH picked AS (
                SELECT c.phone
                FROM conversations c
                WHERE {where_sql}
                ORDER BY c.updated_at DESC
                LIMIT :limit
            )
            INSERT INTO campaign_recipients (campaign_id, phone, status, created_at)
            SELECT :campaign_id, p.phone, 'pending', NOW()
            FROM picked p
            ON CONFLICT (campaign_id, phone) DO NOTHING
        """), seg_params)

        status = "scheduled" if campaign.get("scheduled_at") and campaign.get("scheduled_at") > now else "running"
        launched_at = None if status == "scheduled" else now

        conn.execute(text("""
            UPDATE campaigns
            SET status = :status,
                launched_at = COALESCE(:launched_at, launched_at),
                updated_at = NOW()
            WHERE id = :campaign_id
        """), {"status": status, "launched_at": launched_at, "campaign_id": int(campaign_id)})

        stats = conn.execute(text("""
            SELECT
                COUNT(*) AS total_recipients,
                COUNT(*) FILTER (WHERE LOWER(status) = 'pending') AS pending
            FROM campaign_recipients
            WHERE campaign_id = :campaign_id
        """), {"campaign_id": int(campaign_id)}).mappings().first()

    return {
        "ok": True,
        "campaign_id": int(campaign_id),
        "status": status,
        "total_recipients": int((stats or {}).get("total_recipients") or 0),
        "pending": int((stats or {}).get("pending") or 0),
    }


@app.get("/api/campaigns/{campaign_id}/stats")
def campaign_stats(campaign_id: int):
    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE LOWER(status) = 'pending') AS pending,
                COUNT(*) FILTER (WHERE LOWER(status) = 'processing') AS processing,
                COUNT(*) FILTER (WHERE LOWER(status) = 'sent') AS sent,
                COUNT(*) FILTER (WHERE LOWER(status) = 'delivered') AS delivered,
                COUNT(*) FILTER (WHERE LOWER(status) = 'read') AS read,
                COUNT(*) FILTER (WHERE LOWER(status) = 'replied') AS replied,
                COUNT(*) FILTER (WHERE LOWER(status) = 'failed') AS failed
            FROM campaign_recipients
            WHERE campaign_id = :campaign_id
        """), {"campaign_id": int(campaign_id)}).mappings().first()

    d = dict(row or {})
    sent = int(d.get("sent") or 0)
    delivered = int(d.get("delivered") or 0)
    read = int(d.get("read") or 0)
    replied = int(d.get("replied") or 0)
    total = int(d.get("total") or 0)

    return {
        "campaign_id": int(campaign_id),
        "total": total,
        "pending": int(d.get("pending") or 0),
        "processing": int(d.get("processing") or 0),
        "sent": sent,
        "delivered": delivered,
        "read": read,
        "replied": replied,
        "failed": int(d.get("failed") or 0),
        "delivery_rate_pct": round((delivered / sent) * 100, 2) if sent else 0.0,
        "read_rate_pct": round((read / delivered) * 100, 2) if delivered else 0.0,
        "reply_rate_pct": round((replied / read) * 100, 2) if read else 0.0,
        "coverage_pct": round((sent / total) * 100, 2) if total else 0.0,
    }


@app.get("/api/campaigns/engine/status")
def campaign_engine_status():
    cfg = engine_settings()
    running = bool(_campaign_engine_task and not _campaign_engine_task.done())
    return {
        "enabled": bool(cfg.get("enabled")),
        "running": running,
        "interval_sec": int(cfg.get("interval_sec") or 0),
        "batch_size": int(cfg.get("batch_size") or 0),
        "send_delay_ms": int(cfg.get("send_delay_ms") or 0),
    }


@app.post("/api/campaigns/engine/tick")
async def campaign_engine_tick_now(
    batch_size: int = Query(20, ge=1, le=500),
    send_delay_ms: int = Query(0, ge=0, le=2000),
):
    data = await campaign_engine_tick(batch_size=batch_size, send_delay_ms=send_delay_ms)
    return data


# =========================================================
# Triggers
# =========================================================

@app.get("/api/triggers/catalog")
def triggers_catalog():
    return get_trigger_catalog()


@app.get("/api/triggers")
def list_triggers(
    active: str = Query("all", description="all|yes|no"),
    channel: str = Query("whatsapp", description="whatsapp|facebook|instagram|tiktok|all"),
):
    active = (active or "all").strip().lower()
    channel = (channel or "whatsapp").strip().lower()
    where: List[str] = []
    if active == "yes":
        where.append("t.is_active = TRUE")
    elif active == "no":
        where.append("t.is_active = FALSE")

    params: Dict[str, Any] = {}
    if channel != "all":
        where.append("LOWER(COALESCE(t.channel, 'whatsapp')) = :channel")
        params["channel"] = _normalize_channel(channel, default="whatsapp")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    with engine.begin() as conn:
        rows = conn.execute(text(f"""
            SELECT
                t.id, t.name, t.event_type, t.trigger_type, t.flow_event,
                t.channel,
                t.conditions_json, t.action_json,
                t.cooldown_minutes, t.is_active, t.last_run_at, t.created_at, t.updated_at,
                t.assistant_enabled, t.assistant_message_type,
                t.priority, t.block_ai, t.stop_on_match, t.only_when_no_takeover,
                (
                    SELECT COUNT(*)
                    FROM trigger_executions e
                    WHERE e.trigger_id = t.id
                ) AS executions_count,
                (
                    SELECT MAX(e2.executed_at)
                    FROM trigger_executions e2
                    WHERE e2.trigger_id = t.id
                ) AS last_execution_at
            FROM automation_triggers t
            {where_sql}
            ORDER BY t.priority ASC, t.updated_at DESC, t.id DESC
        """), params).mappings().all()

    return {"triggers": [dict(r) for r in rows]}


@app.post("/api/triggers")
def create_trigger(payload: TriggerIn):
    name = (payload.name or "").strip()
    event_type = _normalize_event_type(payload.event_type)
    if not name or not event_type:
        raise HTTPException(status_code=400, detail="name and event_type are required")

    trigger_type = _normalize_trigger_type(payload.trigger_type)
    flow_event = _normalize_flow_event(payload.flow_event)
    assistant_message_type = _normalize_assistant_message_type(payload.assistant_message_type)

    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO automation_triggers (
                channel,
                name, event_type, trigger_type, flow_event,
                conditions_json, action_json,
                cooldown_minutes, is_active,
                assistant_enabled, assistant_message_type,
                priority, block_ai, stop_on_match, only_when_no_takeover,
                created_at, updated_at
            )
            VALUES (
                :channel,
                :name, :event_type, :trigger_type, :flow_event,
                CAST(:conditions_json AS jsonb), CAST(:action_json AS jsonb),
                :cooldown_minutes, :is_active,
                :assistant_enabled, :assistant_message_type,
                :priority, :block_ai, :stop_on_match, :only_when_no_takeover,
                NOW(), NOW()
            )
            RETURNING
                id, name, event_type, trigger_type, flow_event,
                channel,
                conditions_json, action_json, cooldown_minutes, is_active, last_run_at, created_at, updated_at,
                assistant_enabled, assistant_message_type,
                priority, block_ai, stop_on_match, only_when_no_takeover
        """), {
            "channel": _normalize_channel(payload.channel, default="whatsapp"),
            "name": name,
            "event_type": event_type,
            "trigger_type": trigger_type,
            "flow_event": flow_event,
            "conditions_json": json.dumps(_safe_json_dict(payload.conditions_json), ensure_ascii=False),
            "action_json": json.dumps(_safe_json_dict(payload.action_json), ensure_ascii=False),
            "cooldown_minutes": max(0, min(int(payload.cooldown_minutes or 0), 10080)),
            "is_active": bool(payload.is_active),
            "assistant_enabled": bool(payload.assistant_enabled),
            "assistant_message_type": assistant_message_type,
            "priority": max(1, min(int(payload.priority or 100), 9999)),
            "block_ai": bool(payload.block_ai),
            "stop_on_match": bool(payload.stop_on_match),
            "only_when_no_takeover": bool(payload.only_when_no_takeover),
        }).mappings().first()

    return {"trigger": dict(row or {})}


@app.patch("/api/triggers/{trigger_id}")
def update_trigger(trigger_id: int, payload: TriggerPatch):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="no fields to update")

    sets: List[str] = ["updated_at = NOW()"]
    params: Dict[str, Any] = {"trigger_id": int(trigger_id)}

    if "name" in data:
        name = str(data.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name cannot be empty")
        sets.append("name = :name")
        params["name"] = name

    if "channel" in data:
        sets.append("channel = :channel")
        params["channel"] = _normalize_channel(str(data.get("channel") or ""), default="whatsapp")

    if "event_type" in data:
        event_type = _normalize_event_type(str(data.get("event_type") or ""))
        if not event_type:
            raise HTTPException(status_code=400, detail="event_type cannot be empty")
        sets.append("event_type = :event_type")
        params["event_type"] = event_type

    if "trigger_type" in data:
        sets.append("trigger_type = :trigger_type")
        params["trigger_type"] = _normalize_trigger_type(str(data.get("trigger_type") or ""))

    if "flow_event" in data:
        sets.append("flow_event = :flow_event")
        params["flow_event"] = _normalize_flow_event(str(data.get("flow_event") or ""))

    if "conditions_json" in data:
        sets.append("conditions_json = CAST(:conditions_json AS jsonb)")
        params["conditions_json"] = json.dumps(_safe_json_dict(data.get("conditions_json")), ensure_ascii=False)

    if "action_json" in data:
        sets.append("action_json = CAST(:action_json AS jsonb)")
        params["action_json"] = json.dumps(_safe_json_dict(data.get("action_json")), ensure_ascii=False)

    if "cooldown_minutes" in data:
        sets.append("cooldown_minutes = :cooldown_minutes")
        params["cooldown_minutes"] = max(0, min(int(data.get("cooldown_minutes") or 0), 10080))

    if "is_active" in data:
        sets.append("is_active = :is_active")
        params["is_active"] = bool(data.get("is_active"))

    if "assistant_enabled" in data:
        sets.append("assistant_enabled = :assistant_enabled")
        params["assistant_enabled"] = bool(data.get("assistant_enabled"))

    if "assistant_message_type" in data:
        sets.append("assistant_message_type = :assistant_message_type")
        params["assistant_message_type"] = _normalize_assistant_message_type(str(data.get("assistant_message_type") or ""))

    if "priority" in data:
        sets.append("priority = :priority")
        params["priority"] = max(1, min(int(data.get("priority") or 100), 9999))

    if "block_ai" in data:
        sets.append("block_ai = :block_ai")
        params["block_ai"] = bool(data.get("block_ai"))

    if "stop_on_match" in data:
        sets.append("stop_on_match = :stop_on_match")
        params["stop_on_match"] = bool(data.get("stop_on_match"))

    if "only_when_no_takeover" in data:
        sets.append("only_when_no_takeover = :only_when_no_takeover")
        params["only_when_no_takeover"] = bool(data.get("only_when_no_takeover"))

    with engine.begin() as conn:
        row = conn.execute(text(f"""
            UPDATE automation_triggers
            SET {", ".join(sets)}
            WHERE id = :trigger_id
            RETURNING
                id, name, event_type, trigger_type, flow_event,
                channel,
                conditions_json, action_json, cooldown_minutes, is_active, last_run_at, created_at, updated_at,
                assistant_enabled, assistant_message_type,
                priority, block_ai, stop_on_match, only_when_no_takeover
        """), params).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="trigger not found")

    return {"trigger": dict(row)}


@app.delete("/api/triggers/{trigger_id}")
def delete_trigger(trigger_id: int):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, name
                FROM automation_triggers
                WHERE id = :trigger_id
                LIMIT 1
                """
            ),
            {"trigger_id": int(trigger_id)},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="trigger not found")

        stats = conn.execute(
            text(
                """
                SELECT
                    (
                        SELECT COUNT(*)
                        FROM trigger_executions e
                        WHERE e.trigger_id = :trigger_id
                    ) AS executions_count,
                    (
                        SELECT COUNT(*)
                        FROM trigger_scheduled_messages sm
                        WHERE sm.trigger_id = :trigger_id
                          AND LOWER(sm.status) IN ('pending', 'processing')
                    ) AS queued_count
                """
            ),
            {"trigger_id": int(trigger_id)},
        ).mappings().first()

        conn.execute(
            text(
                """
                DELETE FROM trigger_scheduled_messages
                WHERE trigger_id = :trigger_id
                  AND LOWER(status) IN ('pending', 'processing')
                """
            ),
            {"trigger_id": int(trigger_id)},
        )

        conn.execute(
            text(
                """
                DELETE FROM automation_triggers
                WHERE id = :trigger_id
                """
            ),
            {"trigger_id": int(trigger_id)},
        )

    return {
        "ok": True,
        "deleted": {"id": int(row.get("id") or 0), "name": str(row.get("name") or "").strip()},
        "cascade": {
            "trigger_executions": int((stats or {}).get("executions_count") or 0),
            "trigger_scheduled_cancelled": int((stats or {}).get("queued_count") or 0),
        },
    }


@app.post("/api/triggers/{trigger_id}/copy")
def copy_trigger_to_channel(trigger_id: int, payload: ChannelCopyIn):
    target_channel = _normalize_channel(payload.target_channel, default="")
    if not target_channel:
        raise HTTPException(status_code=400, detail="target_channel invalid")

    suffix = str(payload.name_suffix or "").strip()

    with engine.begin() as conn:
        src = conn.execute(
            text(
                """
                SELECT
                    id, name, channel, event_type, trigger_type, flow_event,
                    conditions_json, action_json, cooldown_minutes, is_active,
                    assistant_enabled, assistant_message_type,
                    priority, block_ai, stop_on_match, only_when_no_takeover
                FROM automation_triggers
                WHERE id = :trigger_id
                LIMIT 1
                """
            ),
            {"trigger_id": int(trigger_id)},
        ).mappings().first()
        if not src:
            raise HTTPException(status_code=404, detail="trigger not found")

        src_channel = _normalize_channel(str(src.get("channel") or "whatsapp"), default="whatsapp")
        if src_channel == target_channel:
            raise HTTPException(status_code=409, detail="trigger already in target channel")

        base_name = str(src.get("name") or "").strip() or f"Trigger {int(trigger_id)}"
        new_name = f"{base_name} {suffix}".strip() if suffix else f"{base_name} [{target_channel}]"

        row = conn.execute(
            text(
                """
                INSERT INTO automation_triggers (
                    name, channel, event_type, trigger_type, flow_event,
                    conditions_json, action_json,
                    cooldown_minutes, is_active,
                    assistant_enabled, assistant_message_type,
                    priority, block_ai, stop_on_match, only_when_no_takeover,
                    created_at, updated_at
                )
                VALUES (
                    :name, :channel, :event_type, :trigger_type, :flow_event,
                    CAST(:conditions_json AS jsonb), CAST(:action_json AS jsonb),
                    :cooldown_minutes, :is_active,
                    :assistant_enabled, :assistant_message_type,
                    :priority, :block_ai, :stop_on_match, :only_when_no_takeover,
                    NOW(), NOW()
                )
                RETURNING
                    id, name, channel, event_type, trigger_type, flow_event,
                    conditions_json, action_json, cooldown_minutes, is_active,
                    assistant_enabled, assistant_message_type,
                    priority, block_ai, stop_on_match, only_when_no_takeover, created_at, updated_at
                """
            ),
            {
                "name": new_name[:180],
                "channel": target_channel,
                "event_type": _normalize_event_type(str(src.get("event_type") or "message_in")),
                "trigger_type": _normalize_trigger_type(str(src.get("trigger_type") or "message_flow")),
                "flow_event": _normalize_flow_event(str(src.get("flow_event") or "received")),
                "conditions_json": json.dumps(_safe_json_dict(src.get("conditions_json")), ensure_ascii=False),
                "action_json": json.dumps(_safe_json_dict(src.get("action_json")), ensure_ascii=False),
                "cooldown_minutes": max(0, min(int(src.get("cooldown_minutes") or 0), 10080)),
                "is_active": bool(src.get("is_active")),
                "assistant_enabled": bool(src.get("assistant_enabled")),
                "assistant_message_type": _normalize_assistant_message_type(str(src.get("assistant_message_type") or "auto")),
                "priority": max(1, min(int(src.get("priority") or 100), 9999)),
                "block_ai": bool(src.get("block_ai")),
                "stop_on_match": bool(src.get("stop_on_match")),
                "only_when_no_takeover": bool(src.get("only_when_no_takeover")),
            },
        ).mappings().first()

    return {"ok": True, "source_trigger_id": int(trigger_id), "trigger": dict(row or {})}


# =========================================================
# Remarketing
# =========================================================

@app.get("/api/remarketing/flows")
def list_remarketing_flows(
    channel: str = Query("whatsapp", description="whatsapp|facebook|instagram|tiktok|all"),
):
    channel = (channel or "whatsapp").strip().lower()
    where_sql = ""
    params: Dict[str, Any] = {}
    if channel != "all":
        where_sql = "WHERE LOWER(COALESCE(f.channel, 'whatsapp')) = :channel"
        params["channel"] = _normalize_channel(channel, default="whatsapp")

    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT
                f.id, f.name, f.channel, f.entry_rules_json, f.exit_rules_json, f.is_active, f.created_at, f.updated_at,
                (
                    SELECT COUNT(*)
                    FROM remarketing_steps s
                    WHERE s.flow_id = f.id
                ) AS steps_count
            FROM remarketing_flows f
            {where_sql}
            ORDER BY f.updated_at DESC, f.id DESC
        """.replace("{where_sql}", where_sql)), params).mappings().all()

    return {"flows": [dict(r) for r in rows]}


@app.post("/api/remarketing/flows")
def create_remarketing_flow(payload: RemarketingFlowIn):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO remarketing_flows (
                name, channel, entry_rules_json, exit_rules_json, is_active, created_at, updated_at
            )
            VALUES (
                :name, :channel, CAST(:entry_rules_json AS jsonb), CAST(:exit_rules_json AS jsonb), :is_active, NOW(), NOW()
            )
            RETURNING id, name, channel, entry_rules_json, exit_rules_json, is_active, created_at, updated_at
        """), {
            "name": name,
            "channel": _normalize_channel(payload.channel, default="whatsapp"),
            "entry_rules_json": json.dumps(_safe_json_dict(payload.entry_rules_json), ensure_ascii=False),
            "exit_rules_json": json.dumps(_safe_json_dict(payload.exit_rules_json), ensure_ascii=False),
            "is_active": bool(payload.is_active),
        }).mappings().first()

    return {"flow": dict(row or {})}


@app.patch("/api/remarketing/flows/{flow_id}")
def update_remarketing_flow(flow_id: int, payload: RemarketingFlowPatch):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="no fields to update")

    sets: List[str] = ["updated_at = NOW()"]
    params: Dict[str, Any] = {"flow_id": int(flow_id)}

    if "name" in data:
        name = str(data.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name cannot be empty")
        sets.append("name = :name")
        params["name"] = name

    if "channel" in data:
        sets.append("channel = :channel")
        params["channel"] = _normalize_channel(str(data.get("channel") or ""), default="whatsapp")

    if "entry_rules_json" in data:
        sets.append("entry_rules_json = CAST(:entry_rules_json AS jsonb)")
        params["entry_rules_json"] = json.dumps(_safe_json_dict(data.get("entry_rules_json")), ensure_ascii=False)

    if "exit_rules_json" in data:
        sets.append("exit_rules_json = CAST(:exit_rules_json AS jsonb)")
        params["exit_rules_json"] = json.dumps(_safe_json_dict(data.get("exit_rules_json")), ensure_ascii=False)

    if "is_active" in data:
        sets.append("is_active = :is_active")
        params["is_active"] = bool(data.get("is_active"))

    with engine.begin() as conn:
        row = conn.execute(text(f"""
            UPDATE remarketing_flows
            SET {", ".join(sets)}
            WHERE id = :flow_id
            RETURNING id, name, channel, entry_rules_json, exit_rules_json, is_active, created_at, updated_at
        """), params).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="flow not found")

    return {"flow": dict(row)}


@app.delete("/api/remarketing/flows/{flow_id}")
def delete_remarketing_flow(flow_id: int):
    def _split_tags_csv(raw: str) -> List[str]:
        out: List[str] = []
        seen = set()
        for item in str(raw or "").split(","):
            token = str(item or "").strip().lower()
            if not token or token in seen:
                continue
            seen.add(token)
            out.append(token)
        return out

    def _join_tags_csv(tags: List[str]) -> str:
        out: List[str] = []
        seen = set()
        for item in tags:
            token = str(item or "").strip().lower()
            if not token or token in seen:
                continue
            seen.add(token)
            out.append(token)
        return ",".join(out)

    with engine.begin() as conn:
        flow = conn.execute(
            text(
                """
                SELECT id, name
                FROM remarketing_flows
                WHERE id = :flow_id
                LIMIT 1
                """
            ),
            {"flow_id": int(flow_id)},
        ).mappings().first()
        if not flow:
            raise HTTPException(status_code=404, detail="flow not found")

        stats = conn.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM remarketing_steps s WHERE s.flow_id = :flow_id) AS steps_count,
                    (SELECT COUNT(*) FROM remarketing_enrollments e WHERE e.flow_id = :flow_id) AS enrollments_count
                """
            ),
            {"flow_id": int(flow_id)},
        ).mappings().first()

        phones = conn.execute(
            text(
                """
                SELECT DISTINCT e.phone, COALESCE(c.tags, '') AS tags
                FROM remarketing_enrollments e
                LEFT JOIN conversations c ON c.phone = e.phone
                WHERE e.flow_id = :flow_id
                """
            ),
            {"flow_id": int(flow_id)},
        ).mappings().all()

        prefix = f"rmk_{int(flow_id)}_"
        tags_cleaned = 0
        for row in phones:
            phone = str(row.get("phone") or "").strip()
            if not phone:
                continue
            tags = _split_tags_csv(str(row.get("tags") or ""))
            filtered = [t for t in tags if not t.startswith(prefix)]
            if not any(t.startswith("rmk_") for t in filtered):
                filtered = [t for t in filtered if t != "remarketing"]
            new_csv = _join_tags_csv(filtered)
            if new_csv != ",".join(tags):
                conn.execute(
                    text(
                        """
                        UPDATE conversations
                        SET tags = :tags,
                            updated_at = NOW()
                        WHERE phone = :phone
                        """
                    ),
                    {"phone": phone, "tags": new_csv},
                )
                tags_cleaned += 1

        conn.execute(
            text(
                """
                DELETE FROM remarketing_flows
                WHERE id = :flow_id
                """
            ),
            {"flow_id": int(flow_id)},
        )

    return {
        "ok": True,
        "deleted": {"id": int(flow.get("id") or 0), "name": str(flow.get("name") or "").strip()},
        "cascade": {
            "steps": int((stats or {}).get("steps_count") or 0),
            "enrollments": int((stats or {}).get("enrollments_count") or 0),
            "conversation_tags_cleaned": int(tags_cleaned),
        },
    }


@app.post("/api/remarketing/flows/{flow_id}/copy")
def copy_remarketing_flow_to_channel(flow_id: int, payload: ChannelCopyIn):
    target_channel = _normalize_channel(payload.target_channel, default="")
    if not target_channel:
        raise HTTPException(status_code=400, detail="target_channel invalid")

    suffix = str(payload.name_suffix or "").strip()

    with engine.begin() as conn:
        flow = conn.execute(
            text(
                """
                SELECT id, name, channel, entry_rules_json, exit_rules_json, is_active
                FROM remarketing_flows
                WHERE id = :flow_id
                LIMIT 1
                """
            ),
            {"flow_id": int(flow_id)},
        ).mappings().first()
        if not flow:
            raise HTTPException(status_code=404, detail="flow not found")

        src_channel = _normalize_channel(str(flow.get("channel") or "whatsapp"), default="whatsapp")
        if src_channel == target_channel:
            raise HTTPException(status_code=409, detail="flow already in target channel")

        steps = conn.execute(
            text(
                """
                SELECT
                    s.step_order,
                    s.stage_name,
                    s.wait_minutes,
                    s.template_id,
                    t.name AS template_name
                FROM remarketing_steps s
                LEFT JOIN message_templates t ON t.id = s.template_id
                WHERE s.flow_id = :flow_id
                ORDER BY s.step_order ASC
                """
            ),
            {"flow_id": int(flow_id)},
        ).mappings().all()

        base_name = str(flow.get("name") or "").strip() or f"Flow {int(flow_id)}"
        new_name = f"{base_name} {suffix}".strip() if suffix else f"{base_name} [{target_channel}]"

        new_flow = conn.execute(
            text(
                """
                INSERT INTO remarketing_flows (
                    name, channel, entry_rules_json, exit_rules_json, is_active, created_at, updated_at
                )
                VALUES (
                    :name, :channel, CAST(:entry_rules_json AS jsonb), CAST(:exit_rules_json AS jsonb), :is_active, NOW(), NOW()
                )
                RETURNING id, name, channel, entry_rules_json, exit_rules_json, is_active, created_at, updated_at
                """
            ),
            {
                "name": new_name[:180],
                "channel": target_channel,
                "entry_rules_json": json.dumps(_safe_json_dict(flow.get("entry_rules_json")), ensure_ascii=False),
                "exit_rules_json": json.dumps(_safe_json_dict(flow.get("exit_rules_json")), ensure_ascii=False),
                "is_active": False,
            },
        ).mappings().first()

        new_flow_id = int((new_flow or {}).get("id") or 0)
        step_copies: List[Dict[str, Any]] = []
        for step in steps:
            template_id = step.get("template_id")
            mapped_template_id = None
            template_name = str(step.get("template_name") or "").strip()
            if template_name:
                tr = conn.execute(
                    text(
                        """
                        SELECT id
                        FROM message_templates
                        WHERE LOWER(name) = :name
                          AND LOWER(COALESCE(channel, 'whatsapp')) = :channel
                        ORDER BY updated_at DESC, id DESC
                        LIMIT 1
                        """
                    ),
                    {"name": template_name.lower(), "channel": target_channel},
                ).mappings().first()
                if tr:
                    mapped_template_id = int(tr.get("id") or 0)

            row = conn.execute(
                text(
                    """
                    INSERT INTO remarketing_steps (
                        flow_id, step_order, stage_name, wait_minutes, template_id, created_at
                    )
                    VALUES (
                        :flow_id, :step_order, :stage_name, :wait_minutes, :template_id, NOW()
                    )
                    RETURNING id, flow_id, step_order, stage_name, wait_minutes, template_id, created_at
                    """
                ),
                {
                    "flow_id": new_flow_id,
                    "step_order": max(1, int(step.get("step_order") or 1)),
                    "stage_name": str(step.get("stage_name") or "").strip(),
                    "wait_minutes": max(0, int(step.get("wait_minutes") or 0)),
                    "template_id": mapped_template_id,
                },
            ).mappings().first()

            step_copies.append(
                {
                    **dict(row or {}),
                    "template_source_id": (int(template_id) if template_id is not None else None),
                    "template_source_name": template_name,
                    "template_mapped_id": mapped_template_id,
                }
            )

    return {
        "ok": True,
        "source_flow_id": int(flow_id),
        "flow": dict(new_flow or {}),
        "steps": step_copies,
    }


@app.get("/api/remarketing/flows/{flow_id}/steps")
def list_remarketing_steps(flow_id: int):
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT
                s.id, s.flow_id, s.step_order, s.stage_name, s.wait_minutes, s.template_id, s.created_at,
                t.name AS template_name
            FROM remarketing_steps s
            LEFT JOIN message_templates t ON t.id = s.template_id
            WHERE s.flow_id = :flow_id
            ORDER BY s.step_order ASC
        """), {"flow_id": int(flow_id)}).mappings().all()

    return {"steps": [dict(r) for r in rows]}


@app.post("/api/remarketing/flows/{flow_id}/steps")
def create_remarketing_step(flow_id: int, payload: RemarketingStepIn):
    stage_name = str(payload.stage_name or "").strip()
    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO remarketing_steps (flow_id, step_order, stage_name, wait_minutes, template_id, created_at)
            VALUES (:flow_id, :step_order, :stage_name, :wait_minutes, :template_id, NOW())
            RETURNING id, flow_id, step_order, stage_name, wait_minutes, template_id, created_at
        """), {
            "flow_id": int(flow_id),
            "step_order": max(1, int(payload.step_order or 1)),
            "stage_name": stage_name,
            "wait_minutes": max(0, int(payload.wait_minutes or 0)),
            "template_id": payload.template_id,
        }).mappings().first()

    return {"step": dict(row or {})}


@app.patch("/api/remarketing/steps/{step_id}")
def update_remarketing_step(step_id: int, payload: RemarketingStepPatch):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="no fields to update")

    sets: List[str] = []
    params: Dict[str, Any] = {"step_id": int(step_id)}

    if "step_order" in data:
        sets.append("step_order = :step_order")
        params["step_order"] = max(1, int(data.get("step_order") or 1))

    if "stage_name" in data:
        sets.append("stage_name = :stage_name")
        params["stage_name"] = str(data.get("stage_name") or "").strip()

    if "wait_minutes" in data:
        sets.append("wait_minutes = :wait_minutes")
        params["wait_minutes"] = max(0, int(data.get("wait_minutes") or 0))

    if "template_id" in data:
        sets.append("template_id = :template_id")
        params["template_id"] = data.get("template_id")

    with engine.begin() as conn:
        row = conn.execute(text(f"""
            UPDATE remarketing_steps
            SET {", ".join(sets)}
            WHERE id = :step_id
            RETURNING id, flow_id, step_order, stage_name, wait_minutes, template_id, created_at
        """), params).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="step not found")

    return {"step": dict(row)}


@app.delete("/api/remarketing/steps/{step_id}")
def delete_remarketing_step(step_id: int):
    with engine.begin() as conn:
        step = conn.execute(
            text(
                """
                SELECT id, flow_id, step_order, stage_name, template_id
                FROM remarketing_steps
                WHERE id = :step_id
                LIMIT 1
                """
            ),
            {"step_id": int(step_id)},
        ).mappings().first()
        if not step:
            raise HTTPException(status_code=404, detail="step not found")

        flow_id = int(step.get("flow_id") or 0)
        old_step_order = int(step.get("step_order") or 0)

        conn.execute(
            text(
                """
                DELETE FROM remarketing_steps
                WHERE id = :step_id
                """
            ),
            {"step_id": int(step_id)},
        )

        remaining = conn.execute(
            text(
                """
                SELECT
                    MIN(step_order) AS first_step_order,
                    COUNT(*) AS steps_count
                FROM remarketing_steps
                WHERE flow_id = :flow_id
                """
            ),
            {"flow_id": flow_id},
        ).mappings().first()

        steps_count = int((remaining or {}).get("steps_count") or 0)
        first_step_order = int((remaining or {}).get("first_step_order") or 0) if steps_count > 0 else 0
        moved_to_hold = False

        if steps_count > 0 and first_step_order > 0:
            rs = conn.execute(
                text(
                    """
                    UPDATE remarketing_enrollments
                    SET current_step_order = :new_step_order,
                        step_started_at = NOW(),
                        next_run_at = NOW(),
                        updated_at = NOW(),
                        meta_json = COALESCE(meta_json, '{}'::jsonb) || CAST(:meta_patch AS jsonb)
                    WHERE flow_id = :flow_id
                      AND current_step_order = :old_step_order
                      AND LOWER(state) IN ('active', 'hold')
                    """
                ),
                {
                    "flow_id": flow_id,
                    "old_step_order": old_step_order,
                    "new_step_order": first_step_order,
                    "meta_patch": '{"step_deleted_reassigned": true}',
                },
            )
        else:
            moved_to_hold = True
            rs = conn.execute(
                text(
                    """
                    UPDATE remarketing_enrollments
                    SET state = 'hold',
                        next_run_at = NULL,
                        updated_at = NOW(),
                        meta_json = COALESCE(meta_json, '{}'::jsonb) || CAST(:meta_patch AS jsonb)
                    WHERE flow_id = :flow_id
                      AND current_step_order = :old_step_order
                      AND LOWER(state) IN ('active', 'hold')
                    """
                ),
                {
                    "flow_id": flow_id,
                    "old_step_order": old_step_order,
                    "meta_patch": '{"step_deleted_without_replacement": true}',
                },
            )

    return {
        "ok": True,
        "deleted": {
            "id": int(step.get("id") or 0),
            "flow_id": int(step.get("flow_id") or 0),
            "step_order": int(step.get("step_order") or 0),
            "stage_name": str(step.get("stage_name") or "").strip(),
            "template_id": step.get("template_id"),
        },
        "enrollment_relinked": int(rs.rowcount or 0),
        "moved_to_hold": bool(moved_to_hold),
        "remaining_steps": int(steps_count),
    }


@app.post("/api/remarketing/flows/{flow_id}/dispatch")
async def dispatch_remarketing_flow_now(flow_id: int, payload: RemarketingDispatchIn):
    safe_limit = max(1, min(int(payload.limit or 600), 5000))
    include_hold = bool(payload.include_hold)

    with engine.begin() as conn:
        flow = conn.execute(
            text(
                """
                SELECT id, name, channel, is_active
                FROM remarketing_flows
                WHERE id = :flow_id
                LIMIT 1
                """
            ),
            {"flow_id": int(flow_id)},
        ).mappings().first()
        if not flow:
            raise HTTPException(status_code=404, detail="flow not found")
        if not bool(flow.get("is_active")):
            raise HTTPException(status_code=409, detail="flow is inactive")
        if _normalize_channel(str(flow.get("channel") or "whatsapp"), default="whatsapp") != "whatsapp":
            raise HTTPException(status_code=409, detail="channel_not_supported_for_dispatch_yet")

        if include_hold:
            rs = conn.execute(
                text(
                    """
                    UPDATE remarketing_enrollments
                    SET state = 'active',
                        step_started_at = NOW(),
                        next_run_at = NOW(),
                        updated_at = NOW(),
                        meta_json = COALESCE(meta_json, '{}'::jsonb) || CAST(:meta_patch AS jsonb)
                    WHERE flow_id = :flow_id
                      AND LOWER(state) IN ('active', 'hold')
                    """
                ),
                {
                    "flow_id": int(flow_id),
                    "meta_patch": '{"manual_flow_dispatch": true, "include_hold": true}',
                },
            )
        else:
            rs = conn.execute(
                text(
                    """
                    UPDATE remarketing_enrollments
                    SET next_run_at = NOW(),
                        updated_at = NOW(),
                        meta_json = COALESCE(meta_json, '{}'::jsonb) || CAST(:meta_patch AS jsonb)
                    WHERE flow_id = :flow_id
                      AND LOWER(state) = 'active'
                    """
                ),
                {
                    "flow_id": int(flow_id),
                    "meta_patch": '{"manual_flow_dispatch": true, "include_hold": false}',
                },
            )

    run_result = await process_due_remarketing(limit=safe_limit, flow_id=int(flow_id))
    return {
        "ok": True,
        "flow_id": int(flow_id),
        "flow_name": str(flow.get("name") or "").strip(),
        "include_hold": include_hold,
        "enrollments_queued": int(rs.rowcount or 0),
        "engine_result": run_result,
    }


@app.post("/api/remarketing/steps/{step_id}/dispatch")
async def dispatch_remarketing_step_now(step_id: int, payload: RemarketingDispatchIn):
    safe_limit = max(1, min(int(payload.limit or 600), 5000))
    include_hold = bool(payload.include_hold)

    with engine.begin() as conn:
        step = conn.execute(
            text(
                """
                SELECT
                    s.id,
                    s.flow_id,
                    s.step_order,
                    s.stage_name,
                    f.name AS flow_name,
                    f.channel AS flow_channel,
                    f.is_active
                FROM remarketing_steps s
                JOIN remarketing_flows f ON f.id = s.flow_id
                WHERE s.id = :step_id
                LIMIT 1
                """
            ),
            {"step_id": int(step_id)},
        ).mappings().first()
        if not step:
            raise HTTPException(status_code=404, detail="step not found")
        if not bool(step.get("is_active")):
            raise HTTPException(status_code=409, detail="flow is inactive")
        if _normalize_channel(str(step.get("flow_channel") or "whatsapp"), default="whatsapp") != "whatsapp":
            raise HTTPException(status_code=409, detail="channel_not_supported_for_dispatch_yet")

        flow_id = int(step.get("flow_id") or 0)
        target_step = int(step.get("step_order") or 0)
        if flow_id <= 0 or target_step <= 0:
            raise HTTPException(status_code=400, detail="invalid step")

        meta_patch = json.dumps(
            {
                "manual_step_dispatch": True,
                "step_id": int(step_id),
                "step_order": int(target_step),
                "include_hold": include_hold,
            },
            ensure_ascii=False,
        )

        if include_hold:
            rs = conn.execute(
                text(
                    """
                    UPDATE remarketing_enrollments
                    SET current_step_order = :target_step,
                        state = 'active',
                        step_started_at = NOW(),
                        next_run_at = NOW(),
                        updated_at = NOW(),
                        meta_json = COALESCE(meta_json, '{}'::jsonb) || CAST(:meta_patch AS jsonb)
                    WHERE flow_id = :flow_id
                      AND LOWER(state) IN ('active', 'hold')
                    """
                ),
                {
                    "flow_id": flow_id,
                    "target_step": target_step,
                    "meta_patch": meta_patch,
                },
            )
        else:
            rs = conn.execute(
                text(
                    """
                    UPDATE remarketing_enrollments
                    SET current_step_order = :target_step,
                        step_started_at = NOW(),
                        next_run_at = NOW(),
                        updated_at = NOW(),
                        meta_json = COALESCE(meta_json, '{}'::jsonb) || CAST(:meta_patch AS jsonb)
                    WHERE flow_id = :flow_id
                      AND LOWER(state) = 'active'
                    """
                ),
                {
                    "flow_id": flow_id,
                    "target_step": target_step,
                    "meta_patch": meta_patch,
                },
            )

    run_result = await process_due_remarketing(limit=safe_limit, flow_id=flow_id)
    return {
        "ok": True,
        "flow_id": int(flow_id),
        "flow_name": str(step.get("flow_name") or "").strip(),
        "step_id": int(step.get("id") or 0),
        "step_order": int(step.get("step_order") or 0),
        "stage_name": str(step.get("stage_name") or "").strip(),
        "include_hold": include_hold,
        "enrollments_queued": int(rs.rowcount or 0),
        "engine_result": run_result,
    }


@app.get("/api/remarketing/flows/{flow_id}/enrollments")
def list_remarketing_enrollments(
    flow_id: int,
    state: str = Query("all", description="all|active|hold|completed|exited"),
    limit: int = Query(200, ge=1, le=2000),
):
    state = (state or "all").strip().lower()
    where_state = ""
    params: Dict[str, Any] = {
        "flow_id": int(flow_id),
        "limit": int(limit),
    }
    if state != "all":
        where_state = "AND LOWER(e.state) = :state"
        params["state"] = state

    with engine.begin() as conn:
        rows = conn.execute(text(f"""
            SELECT
                e.id,
                e.flow_id,
                e.phone,
                e.current_step_order,
                e.state,
                e.enrolled_at,
                e.step_started_at,
                e.next_run_at,
                e.last_sent_at,
                e.last_sent_step_order,
                e.updated_at,
                e.meta_json,
                COALESCE(c.first_name, '') AS first_name,
                COALESCE(c.last_name, '') AS last_name,
                COALESCE(c.tags, '') AS tags,
                s.stage_name AS current_stage_name,
                s.template_id AS current_template_id,
                t.name AS current_template_name
            FROM remarketing_enrollments e
            LEFT JOIN conversations c ON c.phone = e.phone
            LEFT JOIN remarketing_steps s
                ON s.flow_id = e.flow_id
               AND s.step_order = e.current_step_order
            LEFT JOIN message_templates t ON t.id = s.template_id
            WHERE e.flow_id = :flow_id
            {where_state}
            ORDER BY e.updated_at DESC, e.id DESC
            LIMIT :limit
        """), params).mappings().all()

    return {"enrollments": [dict(r) for r in rows]}


@app.get("/api/remarketing/stages/catalog")
def remarketing_stages_catalog(
    channel: str = Query("whatsapp", description="whatsapp|facebook|instagram|tiktok|all"),
):
    ch = (channel or "whatsapp").strip().lower()
    if ch == "all":
        return {"flows": list_stage_catalog(channel=None)}
    return {"flows": list_stage_catalog(channel=_normalize_channel(ch, default="whatsapp"))}


@app.get("/api/remarketing/contacts/{phone}")
def remarketing_contact_state(phone: str):
    p = (phone or "").strip()
    if not p:
        raise HTTPException(status_code=400, detail="phone required")
    return {"phone": p, "enrollments": get_phone_enrollments(p)}


@app.post("/api/remarketing/stage/assign")
def assign_remarketing_stage(payload: RemarketingStageAssignIn):
    result = assign_phone_stage(
        phone=payload.phone,
        flow_id=payload.flow_id,
        stage=payload.stage,
        send_now=bool(payload.send_now),
        source="api",
    )
    if not result.get("ok"):
        detail = str(result.get("error") or "cannot_assign_stage")
        raise HTTPException(status_code=400, detail=detail)
    return result


@app.get("/api/remarketing/engine/status")
def remarketing_engine_status():
    cfg = remarketing_settings()
    running = bool(_remarketing_engine_task and not _remarketing_engine_task.done())
    campaign_running = bool(_campaign_engine_task and not _campaign_engine_task.done())
    return {
        "enabled": bool(cfg.get("enabled")),
        "running": running,
        "runner": ("standalone" if running else "stopped"),
        "interval_sec": int(max(0, int(os.getenv("REMARKETING_ENGINE_INTERVAL_SEC", "8") or 0))),
        "batch_size": int(cfg.get("batch_size") or 0),
        "new_enrollments_per_flow": int(cfg.get("new_enrollments_per_flow") or 0),
        "resume_after_minutes": int(cfg.get("resume_after_minutes") or 0),
        "retry_minutes": int(cfg.get("retry_minutes") or 0),
        "service_window_hours": int(cfg.get("service_window_hours") or 24),
        "campaign_engine_running": campaign_running,
    }


@app.post("/api/remarketing/engine/tick")
async def remarketing_engine_tick_now(
    limit: int = Query(300, ge=1, le=5000),
    flow_id: int = Query(0, ge=0),
    channel: str = Query("whatsapp", description="whatsapp|facebook|instagram|tiktok|all"),
):
    fid = int(flow_id or 0)
    ch = (channel or "whatsapp").strip().lower()
    normalized_channel = None if ch == "all" else _normalize_channel(ch, default="whatsapp")
    return await process_due_remarketing(limit=limit, flow_id=(fid if fid > 0 else None), channel=normalized_channel)


# =========================================================
# SECURITY API
# =========================================================

SECURITY_ROLES = {"admin", "supervisor", "agente"}


def security_rotation_settings() -> Dict[str, Any]:
    raw_enabled = str(os.getenv("SECURITY_KEY_ROTATION_ENABLED", "true") or "true").strip().lower()
    enabled = raw_enabled in {"1", "true", "yes", "on", "y", "si"}
    raw_interval = str(os.getenv("SECURITY_KEY_ROTATION_INTERVAL_SEC", "1800") or "1800").strip()
    try:
        interval_sec = int(raw_interval)
    except Exception:
        interval_sec = 1800
    interval_sec = int(max(30, min(interval_sec, 86400)))
    return {"enabled": enabled, "interval_sec": interval_sec}


def rotate_due_security_keys_once(limit: int = 60) -> Dict[str, Any]:
    safe_limit = int(max(1, min(int(limit or 60), 500)))
    rotated = 0
    scanned = 0
    errors: List[str] = []

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, name, scope, rotation_days
                FROM app_api_keys
                WHERE is_active = TRUE
                  AND COALESCE(rotation_days, 0) > 0
                  AND next_rotation_at IS NOT NULL
                  AND next_rotation_at <= NOW()
                ORDER BY next_rotation_at ASC, id ASC
                LIMIT :limit
                """
            ),
            {"limit": safe_limit},
        ).mappings().all()

        scanned = len(rows)
        for row in rows:
            key_id = int(row.get("id") or 0)
            if key_id <= 0:
                continue
            try:
                plain_secret, preview, secret_hash, secret_cipher = _new_api_secret()
                conn.execute(
                    text(
                        """
                        UPDATE app_api_keys
                        SET
                            secret_preview = :preview,
                            secret_hash = :secret_hash,
                            secret_cipher = :secret_cipher,
                            last_rotated_at = NOW(),
                            next_rotation_at = NOW() + ((COALESCE(NULLIF(rotation_days, 0), 90)::text || ' days')::interval),
                            updated_at = NOW(),
                            is_active = TRUE
                        WHERE id = :key_id
                        """
                    ),
                    {
                        "key_id": key_id,
                        "preview": preview,
                        "secret_hash": secret_hash,
                        "secret_cipher": secret_cipher,
                    },
                )
                rotated += 1
                _audit_security(
                    conn,
                    level="high",
                    action="Rotación automática de API key",
                    actor="Sistema",
                    ip="",
                    details={
                        "key_id": key_id,
                        "name": str(row.get("name") or ""),
                        "scope": str(row.get("scope") or ""),
                        "auto_rotation": True,
                    },
                )
            except Exception as e:
                errors.append(f"id={key_id}:{str(e)[:140]}")

    return {"ok": True, "scanned": scanned, "rotated": rotated, "errors": errors}


class SecurityPolicyPatch(BaseModel):
    password_min_length: Optional[int] = Field(default=None, ge=8, le=128)
    require_special_chars: Optional[bool] = None
    access_token_minutes: Optional[int] = Field(default=None, ge=5, le=240)
    refresh_token_days: Optional[int] = Field(default=None, ge=1, le=180)
    session_idle_minutes: Optional[int] = Field(default=None, ge=5, le=720)
    session_absolute_hours: Optional[int] = Field(default=None, ge=1, le=168)
    max_failed_attempts: Optional[int] = Field(default=None, ge=3, le=20)
    lock_minutes: Optional[int] = Field(default=None, ge=1, le=240)
    force_password_rotation_days: Optional[int] = Field(default=None, ge=15, le=365)


class SecurityMfaPatch(BaseModel):
    enforce_for_admins: Optional[bool] = None
    enforce_for_supervisors: Optional[bool] = None
    allow_for_agents: Optional[bool] = None
    backup_codes_enabled: Optional[bool] = None


class SecurityAlertsPatch(BaseModel):
    failed_login_alert: Optional[bool] = None
    suspicious_ip_alert: Optional[bool] = None
    security_change_alert: Optional[bool] = None
    webhook_failure_alert: Optional[bool] = None
    channel_email: Optional[bool] = None
    channel_whatsapp: Optional[bool] = None


class SecurityUserCreateIn(BaseModel):
    name: str
    email: str
    role: str = "agente"
    twofa: bool = False
    active: bool = True
    password: Optional[str] = None


class SecurityUserPatch(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    twofa: Optional[bool] = None
    active: Optional[bool] = None


class SecurityUserPasswordResetIn(BaseModel):
    password: Optional[str] = None


class SecurityTwofaVerifyIn(BaseModel):
    code: str


class SecurityKeyCreateIn(BaseModel):
    name: str
    scope: str = "general"
    rotation_days: int = Field(default=90, ge=1, le=3650)


class SecurityKeyPatch(BaseModel):
    name: Optional[str] = None
    scope: Optional[str] = None
    is_active: Optional[bool] = None
    rotation_days: Optional[int] = Field(default=None, ge=1, le=3650)


class MobilePushRegisterIn(BaseModel):
    token: str
    platform: str = "android"
    app_version: str = ""
    device_id: str = ""
    role: str = "agente"
    actor: str = ""
    notifications_enabled: bool = True


class MobilePushUnregisterIn(BaseModel):
    token: str


class MobilePushTestIn(BaseModel):
    title: str = "Prueba push Verane"
    body: str = "Push de prueba enviado desde backend"
    event_type: str = "manual_test"
    role_scope: str = "all"
    data: Dict[str, Any] = Field(default_factory=dict)


def _truthy(raw: Any) -> bool:
    return str(raw or "").strip().lower() in {"1", "true", "yes", "on", "y", "si"}


def _fcm_push_enabled() -> bool:
    if _truthy(os.getenv("PUSH_FCM_ENABLED", "true")):
        return True
    return _truthy(os.getenv("FCM_PUSH_ENABLED", "false"))


def _normalize_mobile_role(raw: str) -> str:
    role = str(raw or "agente").strip().lower()
    return role if role in SECURITY_ROLES else "agente"


def _normalize_push_role_scope(raw: str) -> str:
    scope = str(raw or "all").strip().lower()
    if scope in {"all", "admin", "supervisor", "agente", "admin_supervisor"}:
        return scope
    return "all"


def _normalize_mobile_push_token(raw: str) -> str:
    token = str(raw or "").strip()
    # Un token FCM real suele superar 100 chars; 32 es un umbral seguro.
    if len(token) < 32:
        return ""
    return token


def _get_active_mobile_push_tokens(role_scope: str = "all") -> List[str]:
    scope = _normalize_push_role_scope(role_scope)
    where = "WHERE is_active = TRUE AND notifications_enabled = TRUE AND token <> ''"
    params: Dict[str, Any] = {}
    if scope == "admin_supervisor":
        where += " AND LOWER(role) IN ('admin', 'supervisor')"
    elif scope in SECURITY_ROLES:
        where += " AND LOWER(role) = :role"
        params["role"] = scope

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT token
                FROM mobile_push_tokens
                {where}
                ORDER BY last_seen_at DESC, id DESC
                LIMIT 5000
                """
            ),
            params,
        ).mappings().all()

    unique: List[str] = []
    seen = set()
    for r in rows:
        tok = _normalize_mobile_push_token(str((r or {}).get("token") or ""))
        if tok and tok not in seen:
            seen.add(tok)
            unique.append(tok)
    return unique


def _save_mobile_push_event(
    *,
    event_type: str,
    role_scope: str,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]],
    status: str,
    tokens_targeted: int,
    tokens_sent: int,
    tokens_failed: int,
    error: str = "",
) -> None:
    payload = data if isinstance(data, dict) else {}
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO mobile_push_events (
                    event_type, role_scope, title, body, data_json,
                    tokens_targeted, tokens_sent, tokens_failed,
                    status, error, created_at, delivered_at
                )
                VALUES (
                    :event_type, :role_scope, :title, :body, CAST(:data_json AS jsonb),
                    :tokens_targeted, :tokens_sent, :tokens_failed,
                    :status, :error, NOW(),
                    CASE WHEN :status IN ('sent', 'partial') THEN NOW() ELSE NULL END
                )
                """
            ),
            {
                "event_type": str(event_type or "generic")[:120],
                "role_scope": _normalize_push_role_scope(role_scope),
                "title": str(title or "")[:200],
                "body": str(body or "")[:500],
                "data_json": json.dumps(payload, ensure_ascii=False),
                "tokens_targeted": int(max(0, tokens_targeted)),
                "tokens_sent": int(max(0, tokens_sent)),
                "tokens_failed": int(max(0, tokens_failed)),
                "status": str(status or "queued")[:40],
                "error": str(error or "")[:900],
            },
        )


def _get_firebase_admin_app() -> tuple[Any, str]:
    global _firebase_admin_app

    if not _fcm_push_enabled():
        return None, "push_disabled_by_env"

    try:
        import firebase_admin  # type: ignore
        from firebase_admin import credentials  # type: ignore
    except Exception:
        return None, "firebase_admin_not_installed"

    if _firebase_admin_app is not None:
        return _firebase_admin_app, "ok"

    try:
        if getattr(firebase_admin, "_apps", None):
            _firebase_admin_app = firebase_admin.get_app()
            return _firebase_admin_app, "ok"
    except Exception:
        pass

    try:
        service_account_json = str(os.getenv("FCM_SERVICE_ACCOUNT_JSON", "") or "").strip()
        service_account_file = str(
            os.getenv("FCM_SERVICE_ACCOUNT_FILE", "") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        ).strip()

        if service_account_json:
            info = json.loads(service_account_json)
            cred = credentials.Certificate(info)
            _firebase_admin_app = firebase_admin.initialize_app(cred)
            return _firebase_admin_app, "ok"

        if service_account_file:
            if not os.path.exists(service_account_file):
                return None, "service_account_file_not_found"
            cred = credentials.Certificate(service_account_file)
            _firebase_admin_app = firebase_admin.initialize_app(cred)
            return _firebase_admin_app, "ok"

        # Fallback a ADC (Application Default Credentials)
        _firebase_admin_app = firebase_admin.initialize_app()
        return _firebase_admin_app, "ok"
    except Exception as e:
        return None, f"firebase_init_error:{str(e)[:300]}"


def _deactivate_mobile_push_tokens(tokens: List[str]) -> None:
    if not tokens:
        return
    clean = [t for t in tokens if _normalize_mobile_push_token(t)]
    if not clean:
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE mobile_push_tokens
                SET is_active = FALSE, updated_at = NOW()
                WHERE token = ANY(:tokens)
                """
            ),
            {"tokens": clean},
        )


def _is_invalid_fcm_token_error(raw: str) -> bool:
    t = str(raw or "").strip().lower()
    return (
        "registration token is not a valid fcm registration token" in t
        or "requested entity was not found" in t
        or "unregistered" in t
        or "registration-token-not-registered" in t
        or "invalid-argument" in t
    )


def _emit_mobile_push_event(
    *,
    event_type: str,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    role_scope: str = "all",
) -> Dict[str, Any]:
    safe_title = str(title or "").strip()[:200] or "Verane"
    safe_body = str(body or "").strip()[:500] or "Nueva notificacion"
    safe_data: Dict[str, str] = {}
    for k, v in (data or {}).items():
        kk = str(k or "").strip()
        if not kk:
            continue
        safe_data[kk[:80]] = str(v if v is not None else "")[:900]
    safe_data.setdefault("event_type", str(event_type or "generic")[:80])

    tokens = _get_active_mobile_push_tokens(role_scope=role_scope)
    if not tokens:
        _save_mobile_push_event(
            event_type=event_type,
            role_scope=role_scope,
            title=safe_title,
            body=safe_body,
            data=safe_data,
            status="no_tokens",
            tokens_targeted=0,
            tokens_sent=0,
            tokens_failed=0,
            error="no_active_tokens",
        )
        return {"ok": True, "status": "no_tokens", "targeted": 0, "sent": 0, "failed": 0}

    app, app_status = _get_firebase_admin_app()
    if app is None:
        _save_mobile_push_event(
            event_type=event_type,
            role_scope=role_scope,
            title=safe_title,
            body=safe_body,
            data=safe_data,
            status="skipped",
            tokens_targeted=len(tokens),
            tokens_sent=0,
            tokens_failed=len(tokens),
            error=app_status,
        )
        return {
            "ok": False,
            "status": "skipped",
            "reason": app_status,
            "targeted": len(tokens),
            "sent": 0,
            "failed": len(tokens),
        }

    try:
        from firebase_admin import messaging  # type: ignore
    except Exception:
        _save_mobile_push_event(
            event_type=event_type,
            role_scope=role_scope,
            title=safe_title,
            body=safe_body,
            data=safe_data,
            status="failed",
            tokens_targeted=len(tokens),
            tokens_sent=0,
            tokens_failed=len(tokens),
            error="firebase_admin.messaging_import_failed",
        )
        return {"ok": False, "status": "failed", "reason": "messaging_import_failed"}

    sent_count = 0
    failed_count = 0
    invalid_tokens: List[str] = []
    error_msgs: List[str] = []

    chunk_size = 500
    for i in range(0, len(tokens), chunk_size):
        chunk = tokens[i:i + chunk_size]
        message = messaging.MulticastMessage(
            tokens=chunk,
            notification=messaging.Notification(title=safe_title, body=safe_body),
            data=safe_data,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id=str((safe_data.get("channel_id") or "verane_messages"))[:120],
                    sound="default",
                ),
            ),
        )
        try:
            response = messaging.send_each_for_multicast(message, app=app)
            sent_count += int(response.success_count or 0)
            failed_count += int(response.failure_count or 0)
            for idx, r in enumerate(response.responses):
                if r.success:
                    continue
                err_txt = str(r.exception or "")[:400]
                if len(error_msgs) < 3 and err_txt:
                    error_msgs.append(err_txt)
                if idx < len(chunk) and _is_invalid_fcm_token_error(err_txt):
                    invalid_tokens.append(chunk[idx])
        except Exception as e:
            failed_count += len(chunk)
            if len(error_msgs) < 3:
                error_msgs.append(str(e)[:400])

    if invalid_tokens:
        _deactivate_mobile_push_tokens(invalid_tokens)

    status = "sent" if failed_count == 0 else ("partial" if sent_count > 0 else "failed")
    _save_mobile_push_event(
        event_type=event_type,
        role_scope=role_scope,
        title=safe_title,
        body=safe_body,
        data=safe_data,
        status=status,
        tokens_targeted=len(tokens),
        tokens_sent=sent_count,
        tokens_failed=failed_count,
        error=" | ".join(error_msgs)[:900],
    )
    return {
        "ok": sent_count > 0 and failed_count == 0,
        "status": status,
        "targeted": len(tokens),
        "sent": sent_count,
        "failed": failed_count,
        "invalid_tokens": len(invalid_tokens),
        "error": " | ".join(error_msgs)[:900],
    }


def _security_role_tokens() -> Dict[str, str]:
    return {
        "admin": str(os.getenv("SECURITY_ADMIN_TOKEN", "") or "").strip(),
        "supervisor": str(os.getenv("SECURITY_SUPERVISOR_TOKEN", "") or "").strip(),
        "agente": str(os.getenv("SECURITY_AGENT_TOKEN", "") or "").strip(),
    }


def _security_auth_enabled() -> bool:
    if _truthy(os.getenv("SECURITY_ENFORCE_AUTH", "")):
        return True
    token_map = _security_role_tokens()
    return any(bool(v) for v in token_map.values())


def _resolve_security_role(request: Optional[StarletteRequest]) -> Optional[str]:
    if request is None:
        return None
    auth = str(request.headers.get("Authorization") or "").strip()
    if not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    if not token:
        return None
    token_map = _security_role_tokens()
    for role, secret_token in token_map.items():
        if secret_token and secrets.compare_digest(token, secret_token):
            return role
    return None


def _require_security_role(request: Optional[StarletteRequest], allowed_roles: set[str]) -> str:
    if not _security_auth_enabled():
        # Modo abierto (desarrollo/legacy): permite operar sin token.
        return "admin"

    role = _resolve_security_role(request)
    if not role:
        raise HTTPException(status_code=401, detail="security bearer token required")
    if role not in allowed_roles:
        raise HTTPException(status_code=403, detail="insufficient security role")
    return role


def _security_actor(request: Optional[StarletteRequest]) -> str:
    if request is None:
        return "Sistema"
    hdr = request.headers.get("X-Actor") or request.headers.get("X-Admin-User") or ""
    actor = str(hdr or "").strip()
    return actor[:120] if actor else "Sistema"


def _security_ip(request: Optional[StarletteRequest]) -> str:
    if request is None:
        return ""
    xfwd = str(request.headers.get("x-forwarded-for") or "").strip()
    if xfwd:
        return xfwd.split(",")[0].strip()[:120]
    client = getattr(request, "client", None)
    host = getattr(client, "host", "") if client else ""
    return str(host or "")[:120]


def _hash_password(password: str, salt_b64: Optional[str] = None) -> tuple[str, str]:
    pwd = str(password or "")
    if not pwd:
        raise ValueError("password required")
    if salt_b64:
        try:
            salt = base64.urlsafe_b64decode((salt_b64 + ("=" * ((4 - len(salt_b64) % 4) % 4))).encode("utf-8"))
        except Exception:
            salt = secrets.token_bytes(16)
    else:
        salt = secrets.token_bytes(16)

    digest = hashlib.pbkdf2_hmac("sha256", pwd.encode("utf-8"), salt, 240000)
    salt_out = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    hash_out = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return salt_out, hash_out


def _verify_password(password: str, salt_b64: str, expected_hash_b64: str) -> bool:
    try:
        _, actual = _hash_password(password, salt_b64=salt_b64)
        return secrets.compare_digest(str(actual or ""), str(expected_hash_b64 or ""))
    except Exception:
        return False


def _generate_temp_password(length: int = 14) -> str:
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%*-_"
    n = int(max(10, min(int(length or 14), 64)))
    return "".join(secrets.choice(chars) for _ in range(n))


def _validate_password_policy(conn, password: str) -> None:
    pwd = str(password or "")
    if not pwd:
        raise HTTPException(status_code=400, detail="password is required")

    row = conn.execute(
        text(
            """
            SELECT
                password_min_length,
                require_special_chars
            FROM security_policy
            WHERE id = 1
            LIMIT 1
            """
        )
    ).mappings().first()

    min_len = int((row or {}).get("password_min_length") or 10)
    require_special = bool((row or {}).get("require_special_chars"))
    if len(pwd) < min_len:
        raise HTTPException(status_code=400, detail=f"password must have at least {min_len} characters")
    if require_special and re.search(r"[^a-zA-Z0-9]", pwd) is None:
        raise HTTPException(status_code=400, detail="password requires at least one special character")


def _totp_generate_secret() -> str:
    try:
        import pyotp  # type: ignore
        return str(pyotp.random_base32())
    except Exception:
        # Fallback base32-like (sin dependencias externas)
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
        return "".join(secrets.choice(alphabet) for _ in range(32))


def _totp_verify(secret: str, code: str) -> bool:
    try:
        import pyotp  # type: ignore
        return bool(pyotp.TOTP(str(secret or "")).verify(str(code or "").strip(), valid_window=1))
    except Exception:
        return False


def _totp_uri(secret: str, email: str) -> str:
    acct = str(email or "usuario").strip() or "usuario"
    issuer = str(os.getenv("SECURITY_2FA_ISSUER", "Verane CRM")).strip() or "Verane CRM"
    try:
        import pyotp  # type: ignore
        return str(pyotp.totp.TOTP(secret).provisioning_uri(name=acct, issuer_name=issuer))
    except Exception:
        return f"otpauth://totp/{issuer}:{acct}?secret={secret}&issuer={issuer}"


def _security_data_key() -> bytes:
    raw = str(os.getenv("SECURITY_DATA_KEY", "") or "").strip()
    if raw:
        # Acepta base64 urlsafe o texto plano.
        try:
            padded = raw + ("=" * ((4 - len(raw) % 4) % 4))
            decoded = base64.urlsafe_b64decode(padded.encode("utf-8"))
            if decoded:
                return hashlib.sha256(decoded).digest()
        except Exception:
            pass
        return hashlib.sha256(raw.encode("utf-8")).digest()

    # Fallback determinístico para no romper despliegues legacy sin key explícita.
    seed = "|".join(
        [
            str(os.getenv("DATABASE_URL", "") or ""),
            str(os.getenv("SECURITY_ADMIN_TOKEN", "") or ""),
            str(os.getenv("SECURITY_SUPERVISOR_TOKEN", "") or ""),
            str(os.getenv("SECURITY_AGENT_TOKEN", "") or ""),
        ]
    )
    return hashlib.sha256(seed.encode("utf-8")).digest()


def _encrypt_security_secret(plain: str) -> str:
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except Exception as e:
        raise RuntimeError(
            "Missing dependency 'cryptography'. Install backend requirements before enabling encrypted secrets."
        ) from e

    key = _security_data_key()
    nonce = secrets.token_bytes(12)
    aesgcm = AESGCM(key)
    cipher = aesgcm.encrypt(nonce, str(plain or "").encode("utf-8"), None)
    payload = base64.urlsafe_b64encode(nonce + cipher).decode("ascii")
    return f"v1:{payload}"


def _decrypt_security_secret(cipher_text: str) -> str:
    raw = str(cipher_text or "").strip()
    if not raw:
        return ""
    if not raw.startswith("v1:"):
        raise ValueError("Unsupported encrypted secret format")
    blob = raw.split(":", 1)[1]
    padded = blob + ("=" * ((4 - len(blob) % 4) % 4))
    data = base64.urlsafe_b64decode(padded.encode("utf-8"))
    if len(data) < 13:
        raise ValueError("Corrupted encrypted secret")

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except Exception as e:
        raise RuntimeError(
            "Missing dependency 'cryptography'. Install backend requirements before decrypting secrets."
        ) from e

    nonce, cipher = data[:12], data[12:]
    aesgcm = AESGCM(_security_data_key())
    plain = aesgcm.decrypt(nonce, cipher, None)
    return plain.decode("utf-8")


def _new_api_secret() -> tuple[str, str, str, str]:
    raw = f"vk_{secrets.token_urlsafe(24)}"
    secret_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    preview = f"{raw[:4]}...{raw[-4:]}"
    secret_cipher = _encrypt_security_secret(raw)
    return raw, preview, secret_hash, secret_cipher


def _security_mobile_alerts_enabled(conn) -> bool:
    try:
        row = conn.execute(
            text(
                """
                SELECT
                    COALESCE(security_change_alert, TRUE) AS security_change_alert,
                    COALESCE(channel_whatsapp, TRUE) AS channel_whatsapp
                FROM security_alert_settings
                WHERE id = 1
                LIMIT 1
                """
            )
        ).mappings().first() or {}
        return bool(row.get("security_change_alert")) and bool(row.get("channel_whatsapp"))
    except Exception:
        return False


def _audit_security(
    conn,
    *,
    level: str,
    action: str,
    actor: str,
    ip: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    level_clean = str(level or "low").strip().lower()
    if level_clean not in {"low", "medium", "high"}:
        level_clean = "low"
    payload = json.dumps(details or {}, ensure_ascii=False)
    conn.execute(
        text(
            """
            INSERT INTO security_audit_events (level, action, actor, ip, details_json, created_at)
            VALUES (:level, :action, :actor, :ip, CAST(:details AS jsonb), NOW())
            """
        ),
        {
            "level": level_clean,
            "action": str(action or "").strip()[:240] or "Evento de seguridad",
            "actor": str(actor or "Sistema").strip()[:120] or "Sistema",
            "ip": str(ip or "").strip()[:120],
            "details": payload,
        },
    )

    if level_clean == "high":
        try:
            if _security_mobile_alerts_enabled(conn):
                _emit_mobile_push_event(
                    event_type="security_alert",
                    title="Alerta de seguridad",
                    body=f"{str(action or 'Evento de seguridad')[:160]}",
                    data={
                        "level": level_clean,
                        "actor": str(actor or "Sistema")[:120],
                        "ip": str(ip or "")[:120],
                        "channel_id": "verane_system",
                    },
                    role_scope="admin_supervisor",
                )
        except Exception as e:
            print("[PUSH] security alert event error:", str(e)[:400])


def _load_security_payload(conn, *, audit_level: str = "all", audit_limit: int = 30) -> Dict[str, Any]:
    policy = conn.execute(
        text(
            """
            SELECT
                password_min_length,
                require_special_chars,
                access_token_minutes,
                refresh_token_days,
                session_idle_minutes,
                session_absolute_hours,
                max_failed_attempts,
                lock_minutes,
                force_password_rotation_days,
                updated_at
            FROM security_policy
            WHERE id = 1
            LIMIT 1
            """
        )
    ).mappings().first()

    mfa = conn.execute(
        text(
            """
            SELECT
                enforce_for_admins,
                enforce_for_supervisors,
                allow_for_agents,
                backup_codes_enabled,
                updated_at
            FROM security_mfa_settings
            WHERE id = 1
            LIMIT 1
            """
        )
    ).mappings().first()

    alerts = conn.execute(
        text(
            """
            SELECT
                failed_login_alert,
                suspicious_ip_alert,
                security_change_alert,
                webhook_failure_alert,
                channel_email,
                channel_whatsapp,
                updated_at
            FROM security_alert_settings
            WHERE id = 1
            LIMIT 1
            """
        )
    ).mappings().first()

    users_rows = conn.execute(
        text(
            """
            SELECT
                id,
                name,
                email,
                role,
                twofa,
                is_active AS active,
                last_login_at AS last_login,
                created_at,
                updated_at
            FROM app_users
            ORDER BY id DESC
            """
        )
    ).mappings().all()

    sessions_rows = conn.execute(
        text(
            """
            SELECT
                s.id,
                COALESCE(u.name, '') AS "user",
                s.device,
                s.ip,
                s.created_at,
                s.last_seen_at AS last_seen
            FROM app_user_sessions s
            LEFT JOIN app_users u ON u.id = s.user_id
            WHERE s.revoked_at IS NULL
            ORDER BY s.last_seen_at DESC, s.created_at DESC
            LIMIT 400
            """
        )
    ).mappings().all()

    keys_rows = conn.execute(
        text(
            """
            SELECT
                id,
                name,
                scope,
                secret_preview AS value,
                is_active,
                rotation_days,
                next_rotation_at,
                last_rotated_at,
                updated_at,
                created_at
            FROM app_api_keys
            ORDER BY updated_at DESC, id DESC
            LIMIT 500
            """
        )
    ).mappings().all()

    level = str(audit_level or "all").strip().lower()
    where = ""
    params: Dict[str, Any] = {"limit": int(max(1, min(int(audit_limit or 30), 300)))}
    if level in {"high", "medium", "low"}:
        where = "WHERE LOWER(level) = :level"
        params["level"] = level

    audit_rows = conn.execute(
        text(
            f"""
            SELECT id, level, action, actor, ip, created_at
            FROM security_audit_events
            {where}
            ORDER BY created_at DESC, id DESC
            LIMIT :limit
            """
        ),
        params,
    ).mappings().all()

    critical_24h = conn.execute(
        text(
            """
            SELECT COUNT(1)
            FROM security_audit_events
            WHERE LOWER(level) = 'high'
              AND created_at >= (NOW() - INTERVAL '24 hours')
            """
        )
    ).scalar_one()

    users = [dict(r) for r in users_rows]
    sessions = [dict(r) for r in sessions_rows]
    keys = [dict(r) for r in keys_rows]
    audit_events = [dict(r) for r in audit_rows]
    active_users = sum(1 for u in users if bool(u.get("active")))
    with_2fa = sum(1 for u in users if bool(u.get("twofa")))

    return {
        "policy": dict(policy or {}),
        "mfa": dict(mfa or {}),
        "alerts": dict(alerts or {}),
        "users": users,
        "sessions": sessions,
        "keys": keys,
        "audit_events": audit_events,
        "summary": {
            "active_users": int(active_users),
            "users_with_2fa": int(with_2fa),
            "total_users": len(users),
            "open_sessions": len(sessions),
            "critical_events_24h": int(critical_24h or 0),
        },
    }


@app.get("/api/security/state")
def get_security_state(
    audit_level: str = Query("all", description="all|high|medium|low"),
    audit_limit: int = Query(50, ge=1, le=300),
    request: StarletteRequest = None,
):
    _require_security_role(request, {"admin", "supervisor"})
    with engine.begin() as conn:
        return _load_security_payload(conn, audit_level=audit_level, audit_limit=audit_limit)


@app.get("/api/security/auth/mode")
def get_security_auth_mode():
    token_map = _security_role_tokens()
    enabled = _security_auth_enabled()
    return {
        "enabled": bool(enabled),
        "open_mode": not bool(enabled),
        "configured_roles": [role for role, tok in token_map.items() if tok],
    }


@app.get("/api/security/rotation/status")
def get_security_rotation_status(request: StarletteRequest):
    _require_security_role(request, {"admin", "supervisor"})
    cfg = security_rotation_settings()
    running = bool(_security_key_rotation_task and not _security_key_rotation_task.done())
    return {
        "enabled": bool(cfg.get("enabled")),
        "running": running,
        "interval_sec": int(cfg.get("interval_sec") or 0),
    }


@app.post("/api/security/rotation/tick")
def run_security_rotation_tick(
    request: StarletteRequest,
    limit: int = Query(60, ge=1, le=500),
):
    _require_security_role(request, {"admin"})
    result = rotate_due_security_keys_once(limit=limit)
    return result


@app.put("/api/security/policy")
def update_security_policy(payload: SecurityPolicyPatch, request: StarletteRequest):
    _require_security_role(request, {"admin"})
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="no fields to update")

    with engine.begin() as conn:
        sets = ["updated_at = NOW()"]
        params: Dict[str, Any] = {}
        for key, val in data.items():
            sets.append(f"{key} = :{key}")
            params[key] = val

        conn.execute(
            text(
                f"""
                UPDATE security_policy
                SET {", ".join(sets)}
                WHERE id = 1
                """
            ),
            params,
        )

        _audit_security(
            conn,
            level="medium",
            action="Actualización de políticas de seguridad",
            actor=_security_actor(request),
            ip=_security_ip(request),
            details={"updated_fields": sorted(list(data.keys()))},
        )

        state = _load_security_payload(conn, audit_level="all", audit_limit=40)
    return {"ok": True, "policy": state.get("policy", {}), "summary": state.get("summary", {})}


@app.put("/api/security/mfa")
def update_security_mfa(payload: SecurityMfaPatch, request: StarletteRequest):
    _require_security_role(request, {"admin"})
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="no fields to update")

    with engine.begin() as conn:
        sets = ["updated_at = NOW()"]
        params: Dict[str, Any] = {}
        for key, val in data.items():
            sets.append(f"{key} = :{key}")
            params[key] = bool(val)

        conn.execute(
            text(
                f"""
                UPDATE security_mfa_settings
                SET {", ".join(sets)}
                WHERE id = 1
                """
            ),
            params,
        )

        _audit_security(
            conn,
            level="medium",
            action="Actualización de política MFA",
            actor=_security_actor(request),
            ip=_security_ip(request),
            details={"updated_fields": sorted(list(data.keys()))},
        )
        state = _load_security_payload(conn, audit_level="all", audit_limit=40)
    return {"ok": True, "mfa": state.get("mfa", {}), "summary": state.get("summary", {})}


@app.put("/api/security/alerts")
def update_security_alerts(payload: SecurityAlertsPatch, request: StarletteRequest):
    _require_security_role(request, {"admin", "supervisor"})
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="no fields to update")

    with engine.begin() as conn:
        sets = ["updated_at = NOW()"]
        params: Dict[str, Any] = {}
        for key, val in data.items():
            sets.append(f"{key} = :{key}")
            params[key] = bool(val)

        conn.execute(
            text(
                f"""
                UPDATE security_alert_settings
                SET {", ".join(sets)}
                WHERE id = 1
                """
            ),
            params,
        )

        _audit_security(
            conn,
            level="low",
            action="Actualización de alertas de seguridad",
            actor=_security_actor(request),
            ip=_security_ip(request),
            details={"updated_fields": sorted(list(data.keys()))},
        )
        state = _load_security_payload(conn, audit_level="all", audit_limit=40)
    return {"ok": True, "alerts": state.get("alerts", {}), "summary": state.get("summary", {})}


@app.post("/api/security/users")
def create_security_user(payload: SecurityUserCreateIn, request: StarletteRequest):
    _require_security_role(request, {"admin"})
    name = str(payload.name or "").strip()
    email = str(payload.email or "").strip().lower()
    role = str(payload.role or "agente").strip().lower()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="valid email is required")
    if role not in SECURITY_ROLES:
        raise HTTPException(status_code=400, detail="invalid role")

    with engine.begin() as conn:
        raw_password = str(payload.password or "").strip() or _generate_temp_password(14)
        _validate_password_policy(conn, raw_password)
        salt, pwh = _hash_password(raw_password)
        requested_twofa = bool(payload.twofa)
        twofa_secret = ""
        twofa_secret_cipher = ""
        twofa_uri = ""
        if requested_twofa:
            twofa_secret = _totp_generate_secret()
            twofa_secret_cipher = _encrypt_security_secret(twofa_secret)
            twofa_uri = _totp_uri(twofa_secret, email)

        exists = conn.execute(
            text("SELECT id FROM app_users WHERE LOWER(email) = :email LIMIT 1"),
            {"email": email},
        ).mappings().first()
        if exists:
            raise HTTPException(status_code=409, detail="email already exists")

        row = conn.execute(
            text(
                """
                INSERT INTO app_users (
                    name, email, role, twofa, is_active,
                    twofa_secret_cipher,
                    password_salt, password_hash, password_updated_at,
                    created_at, updated_at
                )
                VALUES (
                    :name, :email, :role, FALSE, :active,
                    :twofa_secret_cipher,
                    :password_salt, :password_hash, NOW(),
                    NOW(), NOW()
                )
                RETURNING
                    id, name, email, role, twofa, is_active AS active, last_login_at AS last_login, created_at, updated_at
                """
            ),
            {
                "name": name,
                "email": email,
                "role": role,
                "active": bool(payload.active),
                "twofa_secret_cipher": twofa_secret_cipher,
                "password_salt": salt,
                "password_hash": pwh,
            },
        ).mappings().first()

        _audit_security(
            conn,
            level="medium",
            action="Creación de usuario",
            actor=_security_actor(request),
            ip=_security_ip(request),
            details={"email": email, "role": role, "requested_twofa": requested_twofa},
        )

    return {
        "ok": True,
        "user": dict(row or {}),
        "temp_password": raw_password,
        "twofa_pending_setup": requested_twofa,
        "twofa_setup_secret": twofa_secret,
        "twofa_setup_uri": twofa_uri,
    }


@app.patch("/api/security/users/{user_id}")
def patch_security_user(user_id: int, payload: SecurityUserPatch, request: StarletteRequest):
    _require_security_role(request, {"admin"})
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="no fields to update")

    with engine.begin() as conn:
        current = conn.execute(
            text(
                """
                SELECT id, name, email, role, twofa, is_active
                FROM app_users
                WHERE id = :user_id
                LIMIT 1
                """
            ),
            {"user_id": int(user_id)},
        ).mappings().first()
        if not current:
            raise HTTPException(status_code=404, detail="user not found")

        sets = ["updated_at = NOW()"]
        params: Dict[str, Any] = {"user_id": int(user_id)}

        if "name" in data:
            name = str(data.get("name") or "").strip()
            if not name:
                raise HTTPException(status_code=400, detail="name cannot be empty")
            sets.append("name = :name")
            params["name"] = name

        if "email" in data:
            email = str(data.get("email") or "").strip().lower()
            if not email or "@" not in email:
                raise HTTPException(status_code=400, detail="valid email is required")
            exists = conn.execute(
                text("SELECT id FROM app_users WHERE LOWER(email) = :email AND id <> :user_id LIMIT 1"),
                {"email": email, "user_id": int(user_id)},
            ).mappings().first()
            if exists:
                raise HTTPException(status_code=409, detail="email already exists")
            sets.append("email = :email")
            params["email"] = email

        if "role" in data:
            role = str(data.get("role") or "").strip().lower()
            if role not in SECURITY_ROLES:
                raise HTTPException(status_code=400, detail="invalid role")
            sets.append("role = :role")
            params["role"] = role

        if "twofa" in data:
            sets.append("twofa = :twofa")
            params["twofa"] = bool(data.get("twofa"))

        if "active" in data:
            sets.append("is_active = :active")
            params["active"] = bool(data.get("active"))

        row = conn.execute(
            text(
                f"""
                UPDATE app_users
                SET {", ".join(sets)}
                WHERE id = :user_id
                RETURNING
                    id, name, email, role, twofa, is_active AS active, last_login_at AS last_login, created_at, updated_at
                """
            ),
            params,
        ).mappings().first()

        _audit_security(
            conn,
            level="medium",
            action="Actualización de usuario",
            actor=_security_actor(request),
            ip=_security_ip(request),
            details={"user_id": int(user_id), "updated_fields": sorted(list(data.keys()))},
        )

    return {"ok": True, "user": dict(row or {})}


@app.post("/api/security/users/{user_id}/password/reset")
def reset_security_user_password(user_id: int, payload: SecurityUserPasswordResetIn, request: StarletteRequest):
    _require_security_role(request, {"admin"})
    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT id, email FROM app_users WHERE id = :user_id LIMIT 1"),
            {"user_id": int(user_id)},
        ).mappings().first()
        if not exists:
            raise HTTPException(status_code=404, detail="user not found")

        password = str(payload.password or "").strip() or _generate_temp_password(14)
        _validate_password_policy(conn, password)
        salt, pwh = _hash_password(password)
        conn.execute(
            text(
                """
                UPDATE app_users
                SET
                    password_salt = :salt,
                    password_hash = :pwh,
                    password_updated_at = NOW(),
                    updated_at = NOW()
                WHERE id = :user_id
                """
            ),
            {"user_id": int(user_id), "salt": salt, "pwh": pwh},
        )

        _audit_security(
            conn,
            level="high",
            action="Reseteo de contraseña de usuario",
            actor=_security_actor(request),
            ip=_security_ip(request),
            details={"user_id": int(user_id), "email": str(exists.get("email") or "")},
        )

    return {"ok": True, "user_id": int(user_id), "temp_password": password}


@app.post("/api/security/users/{user_id}/2fa/setup")
def setup_security_user_2fa(user_id: int, request: StarletteRequest):
    _require_security_role(request, {"admin"})
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, email
                FROM app_users
                WHERE id = :user_id
                LIMIT 1
                """
            ),
            {"user_id": int(user_id)},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="user not found")

        secret = _totp_generate_secret()
        secret_cipher = _encrypt_security_secret(secret)
        conn.execute(
            text(
                """
                UPDATE app_users
                SET
                    twofa_secret_cipher = :secret_cipher,
                    twofa = FALSE,
                    updated_at = NOW()
                WHERE id = :user_id
                """
            ),
            {"user_id": int(user_id), "secret_cipher": secret_cipher},
        )
        _audit_security(
            conn,
            level="medium",
            action="Configuración inicial 2FA",
            actor=_security_actor(request),
            ip=_security_ip(request),
            details={"user_id": int(user_id), "email": str(row.get("email") or "")},
        )

    return {
        "ok": True,
        "user_id": int(user_id),
        "secret": secret,
        "otpauth_uri": _totp_uri(secret, str(row.get("email") or "")),
    }


@app.post("/api/security/users/{user_id}/2fa/verify")
def verify_security_user_2fa(user_id: int, payload: SecurityTwofaVerifyIn, request: StarletteRequest):
    _require_security_role(request, {"admin"})
    code = str(payload.code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="code is required")

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, email, twofa_secret_cipher
                FROM app_users
                WHERE id = :user_id
                LIMIT 1
                """
            ),
            {"user_id": int(user_id)},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="user not found")
        secret_cipher = str(row.get("twofa_secret_cipher") or "")
        if not secret_cipher:
            raise HTTPException(status_code=409, detail="2FA setup required first")
        secret = _decrypt_security_secret(secret_cipher)
        if not _totp_verify(secret, code):
            raise HTTPException(status_code=400, detail="invalid 2FA code")

        conn.execute(
            text(
                """
                UPDATE app_users
                SET twofa = TRUE, updated_at = NOW()
                WHERE id = :user_id
                """
            ),
            {"user_id": int(user_id)},
        )
        _audit_security(
            conn,
            level="high",
            action="Activación de 2FA",
            actor=_security_actor(request),
            ip=_security_ip(request),
            details={"user_id": int(user_id), "email": str(row.get("email") or "")},
        )

    return {"ok": True, "user_id": int(user_id), "twofa": True}


@app.post("/api/security/users/{user_id}/2fa/disable")
def disable_security_user_2fa(user_id: int, request: StarletteRequest):
    _require_security_role(request, {"admin"})
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id, email FROM app_users WHERE id = :user_id LIMIT 1"),
            {"user_id": int(user_id)},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="user not found")
        conn.execute(
            text(
                """
                UPDATE app_users
                SET
                    twofa = FALSE,
                    twofa_secret_cipher = '',
                    updated_at = NOW()
                WHERE id = :user_id
                """
            ),
            {"user_id": int(user_id)},
        )
        _audit_security(
            conn,
            level="high",
            action="Desactivación de 2FA",
            actor=_security_actor(request),
            ip=_security_ip(request),
            details={"user_id": int(user_id), "email": str(row.get("email") or "")},
        )
    return {"ok": True, "user_id": int(user_id), "twofa": False}


@app.post("/api/security/sessions/{session_id}/revoke")
def revoke_security_session(session_id: str, request: StarletteRequest):
    _require_security_role(request, {"admin", "supervisor"})
    sid = str(session_id or "").strip()
    if not sid:
        raise HTTPException(status_code=400, detail="session_id required")

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE app_user_sessions
                SET revoked_at = NOW()
                WHERE id = :sid
                  AND revoked_at IS NULL
                RETURNING id
                """
            ),
            {"sid": sid},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="session not found or already revoked")

        _audit_security(
            conn,
            level="medium",
            action="Revocación de sesión",
            actor=_security_actor(request),
            ip=_security_ip(request),
            details={"session_id": sid},
        )

    return {"ok": True, "session_id": sid, "revoked": True}


@app.post("/api/security/sessions/revoke-all")
def revoke_all_security_sessions(request: StarletteRequest):
    _require_security_role(request, {"admin"})
    with engine.begin() as conn:
        rs = conn.execute(
            text(
                """
                UPDATE app_user_sessions
                SET revoked_at = NOW()
                WHERE revoked_at IS NULL
                """
            )
        )
        count = int(rs.rowcount or 0)
        _audit_security(
            conn,
            level="high",
            action="Revocación masiva de sesiones",
            actor=_security_actor(request),
            ip=_security_ip(request),
            details={"revoked_count": count},
        )
    return {"ok": True, "revoked_count": count}


@app.post("/api/security/keys")
def create_security_key(payload: SecurityKeyCreateIn, request: StarletteRequest):
    _require_security_role(request, {"admin"})
    name = str(payload.name or "").strip()
    scope = str(payload.scope or "general").strip().lower()
    rotation_days = int(payload.rotation_days or 90)
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if not scope:
        scope = "general"

    plain_secret, preview, secret_hash, secret_cipher = _new_api_secret()
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                INSERT INTO app_api_keys (
                    name, scope, secret_preview, secret_hash, secret_cipher,
                    is_active, rotation_days, last_rotated_at, next_rotation_at,
                    created_at, updated_at
                )
                VALUES (
                    :name, :scope, :preview, :secret_hash, :secret_cipher,
                    TRUE, :rotation_days, NOW(), NOW() + ((:rotation_days::text || ' days')::interval),
                    NOW(), NOW()
                )
                RETURNING
                    id, name, scope, secret_preview AS value, is_active,
                    rotation_days, next_rotation_at, last_rotated_at, updated_at, created_at
                """
            ),
            {
                "name": name,
                "scope": scope,
                "preview": preview,
                "secret_hash": secret_hash,
                "secret_cipher": secret_cipher,
                "rotation_days": rotation_days,
            },
        ).mappings().first()

        _audit_security(
            conn,
            level="high",
            action="Creación de API key",
            actor=_security_actor(request),
            ip=_security_ip(request),
            details={"name": name, "scope": scope, "rotation_days": rotation_days},
        )

    return {"ok": True, "key": dict(row or {}), "plain_secret": plain_secret}


@app.post("/api/security/keys/{key_id}/rotate")
def rotate_security_key(key_id: int, request: StarletteRequest):
    _require_security_role(request, {"admin"})
    plain_secret, preview, secret_hash, secret_cipher = _new_api_secret()

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE app_api_keys
                SET
                    secret_preview = :preview,
                    secret_hash = :secret_hash,
                    secret_cipher = :secret_cipher,
                    updated_at = NOW(),
                    last_rotated_at = NOW(),
                    next_rotation_at = NOW() + ((COALESCE(NULLIF(rotation_days, 0), 90)::text || ' days')::interval),
                    is_active = TRUE
                WHERE id = :key_id
                RETURNING
                    id, name, scope, secret_preview AS value, is_active,
                    rotation_days, next_rotation_at, last_rotated_at, updated_at, created_at
                """
            ),
            {
                "key_id": int(key_id),
                "preview": preview,
                "secret_hash": secret_hash,
                "secret_cipher": secret_cipher,
            },
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="key not found")

        _audit_security(
            conn,
            level="high",
            action="Rotación de API key",
            actor=_security_actor(request),
            ip=_security_ip(request),
            details={
                "key_id": int(key_id),
                "name": str(row.get("name") or ""),
                "next_rotation_at": str(row.get("next_rotation_at") or ""),
            },
        )

    return {"ok": True, "key": dict(row or {}), "plain_secret": plain_secret}


@app.patch("/api/security/keys/{key_id}")
def patch_security_key(key_id: int, payload: SecurityKeyPatch, request: StarletteRequest):
    _require_security_role(request, {"admin"})
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="no fields to update")

    sets = ["updated_at = NOW()"]
    params: Dict[str, Any] = {"key_id": int(key_id)}

    if "name" in data:
        name = str(data.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name cannot be empty")
        sets.append("name = :name")
        params["name"] = name

    if "scope" in data:
        scope = str(data.get("scope") or "").strip().lower()
        if not scope:
            raise HTTPException(status_code=400, detail="scope cannot be empty")
        sets.append("scope = :scope")
        params["scope"] = scope

    if "is_active" in data:
        sets.append("is_active = :is_active")
        params["is_active"] = bool(data.get("is_active"))

    if "rotation_days" in data:
        rotation_days = int(data.get("rotation_days") or 90)
        sets.append("rotation_days = :rotation_days")
        sets.append("next_rotation_at = NOW() + ((:rotation_days::text || ' days')::interval)")
        params["rotation_days"] = rotation_days

    with engine.begin() as conn:
        row = conn.execute(
            text(
                f"""
                UPDATE app_api_keys
                SET {", ".join(sets)}
                WHERE id = :key_id
                RETURNING
                    id, name, scope, secret_preview AS value, is_active,
                    rotation_days, next_rotation_at, last_rotated_at, updated_at, created_at
                """
            ),
            params,
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="key not found")

        _audit_security(
            conn,
            level="medium",
            action="Actualización de API key",
            actor=_security_actor(request),
            ip=_security_ip(request),
            details={"key_id": int(key_id), "updated_fields": sorted(list(data.keys()))},
        )

    return {"ok": True, "key": dict(row or {})}


@app.post("/api/security/keys/{key_id}/reveal")
def reveal_security_key(key_id: int, request: StarletteRequest):
    _require_security_role(request, {"admin"})
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, name, secret_cipher
                FROM app_api_keys
                WHERE id = :key_id
                LIMIT 1
                """
            ),
            {"key_id": int(key_id)},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="key not found")

        plain = _decrypt_security_secret(str(row.get("secret_cipher") or ""))
        _audit_security(
            conn,
            level="high",
            action="Revelado de API key",
            actor=_security_actor(request),
            ip=_security_ip(request),
            details={"key_id": int(key_id), "name": str(row.get("name") or "")},
        )

    return {"ok": True, "key_id": int(key_id), "plain_secret": plain}


@app.get("/api/security/audit")
def list_security_audit(
    level: str = Query("all", description="all|high|medium|low"),
    limit: int = Query(120, ge=1, le=500),
    request: StarletteRequest = None,
):
    _require_security_role(request, {"admin", "supervisor"})
    lvl = str(level or "all").strip().lower()
    where = ""
    params: Dict[str, Any] = {"limit": int(limit)}
    if lvl in {"high", "medium", "low"}:
        where = "WHERE LOWER(level) = :level"
        params["level"] = lvl

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT id, level, action, actor, ip, created_at, details_json
                FROM security_audit_events
                {where}
                ORDER BY created_at DESC, id DESC
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()

    return {"events": [dict(r) for r in rows]}

