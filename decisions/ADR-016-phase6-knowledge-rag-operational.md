# ADR-016 Phase 6 Knowledge/RAG Operational

Date: 2026-05-25

## Status

Accepted

## Context

SaaS Phase 6 required Knowledge Base and RAG to be operational for tenant users: PDF/TXT/CSV upload, visible indexing status, URL ingestion, tenant-scoped retrieval, citations, RAG quality evaluation, manual reindex, and AI usage of retrieved context.

Existing code already had `knowledge/router.py`, `saas_knowledge_sources`, `saas_knowledge_chunks`, retrieval logs, upload, URL ingestion, search, reindex, delete, and AI prompt context. Gaps detected from real code were: search was lexical only, CSV was decoded as plain text, no persisted RAG evaluation workflow existed, and URL ingestion fetched arbitrary URLs without private-network checks.

## Decision

- Add forward migration `041_saas_knowledge_rag_phase6_operational.sql`.
- Store local sparse-vector metadata in `saas_knowledge_chunks.vector_json` and top keywords in `keywords_json`.
- Keep retrieval dependency-light by combining sparse-vector cosine scoring with existing lexical scoring instead of adding pgvector or an external vector database.
- Add tenant-scoped `saas_knowledge_evaluations` for quality score, answerability, pass/fail, citations, expected sources, and metadata.
- Add `/knowledge/evaluate` and `/knowledge/evaluations` without breaking `/knowledge/search`.
- Normalize CSV uploads into column/row text before chunking.
- Harden URL ingestion by rejecting URL credentials, localhost, and private/link-local/reserved network targets before fetch.
- Extend the client Knowledge UI to show vector status, retrieval mode, citations, matched terms, quality summary, evaluation form, and recent evaluations.

## Consequences

- Phase 6 can run on clean PostgreSQL without new package installs.
- Search is more semantically useful than lexical-only search, but it is not pgvector-grade high-scale semantic retrieval.
- Private/intranet crawling is intentionally blocked until a safe allowlist/proxy design exists.
- Production acceptance should still include large PDF/CSV samples and real AI-provider reply smoke with tenant credentials.
