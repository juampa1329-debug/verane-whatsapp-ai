# ADR-058 - Humanized Conversation AI Replies

Date: 2026-05-28

Status: Accepted

## Context

SaaS conversation AI could produce long single-block WhatsApp replies and high request token usage. The runtime already had conversation memory, CRM context, Knowledge/RAG, collective memory, outbound chunking and a best-effort WhatsApp typing indicator, but defaults were too large for natural customer conversations.

## Decision

Conversation AI now defaults to a humanized WhatsApp mode:

- preserve continuity through CRM, conversation memory, facts, Knowledge/RAG, collective memory, approved multimodal context and a bounded recent transcript
- cap conversation reply output to 700 tokens when human style is enabled
- send only a bounded recent raw transcript by default: 16 messages and 1200 chars per message
- split long replies into natural outbound fragments with a default 220-character chunk cap
- preserve delayed outbound queue delivery and existing message quota enforcement
- keep Meta typing indicator as best-effort before generation when the inbound WhatsApp provider message id is available
- expose tenant controls in Settings > IA for style, splitting, output cap, chunking, context window and typing

## Consequences

- Lower average completion size and more natural WhatsApp replies.
- Older conversation continuity relies on memory summary/facts instead of resending every raw message on every request.
- Each fragment remains a real outbound message and consumes outbound message quota.
- Typing indicator behavior depends on Meta Cloud API acceptance and should not be treated as guaranteed telemetry.
- No provider routing, secret handling, tenant isolation, billing enforcement, one-AI-owner behavior or Meta dispatch contract was changed.
