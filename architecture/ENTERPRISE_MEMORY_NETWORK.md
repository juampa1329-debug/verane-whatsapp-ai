# AI Enterprise Memory Network

Scope: SaaS Phase 20.

## Architecture

```text
Collective Memory     Knowledge/RAG      Multimodal Memory      Vertical Insights
        \                  |                    |                       /
         \                 |                    |                      /
          v                v                    v                     v
                 Enterprise Memory Sync
                          |
                          v
        saas_enterprise_memory_nodes + saas_enterprise_memory_edges
                          |
                          v
        Policy enforcement + Review / publish / reject / archive / delete
```

## Runtime Flow

```text
/intelligence/memory-network/sync
  -> feature gate: enterprise_memory_network or ai_premium
  -> dry_run previews candidate nodes
  -> allowed scopes + privacy + customer review policy applied
  -> full mode upserts nodes and root graph edges
  -> operators review nodes
  -> future prompt/RAG consumers may use published tenant nodes only

/intelligence/memory-network/import
  -> full mode required unless dry_run=true
  -> bounded JSON nodes sanitized
  -> imported nodes stored as candidate

/intelligence/memory-network/export
  -> full mode required
  -> returns tenant policy, nodes, edges and safety metadata

/intelligence/memory-network/nodes/{id}
  -> DELETE removes tenant-scoped node and cascades graph edges
  -> access log + Intelligence event recorded
```

## Privacy Rules

- Tenant isolation is mandatory in every query.
- No raw content crosses tenants.
- Raw media/base64 is never persisted.
- Customer-content nodes remain tenant-private and reviewable.
- Cross-agent routing is tenant-internal only.
- Import never publishes directly; imported nodes start as `candidate`.
- Export is tenant-scoped and includes summaries/metadata/hashes only.
- Policy updates archive nodes outside allowed scopes and demote published customer content when review is required.

## Tables

- `saas_enterprise_memory_policies`
- `saas_enterprise_memory_nodes`
- `saas_enterprise_memory_edges`
- `saas_enterprise_memory_sync_runs`
- `saas_enterprise_memory_access_logs`

## Feature Gates

- `enterprise_memory_network`
- `memory_graph`
- `memory_governance`
- `cross_agent_memory_routing`
- `memory_quality_scoring`
- umbrella: `ai_premium`

## Validation Snapshot

- Migration `066` applied on active Docker stack.
- Clean isolated PostgreSQL bootstrap passed through migrations `001-066`.
- OpenAPI includes `/saas/v1/intelligence/memory-network/*`.
- Full-mode tenant smoke synced memory candidates, created nodes/edges and published one node.
