# Ecosystem Implementations and What We Adopted

Snapshot date: 2026-03-08.

## External implementations

1. Vikunja official integrations: https://vikunja.io/docs/integrations/
2. n8n integration docs: https://vikunja.io/docs/integrations/n8n/
3. Vja CLI: https://gitlab.com/go-vikunja/vja
4. tw2vikunja: https://github.com/JohannSteffens/tw2vikunja
5. Cria TUI: https://codeberg.org/alpha_v/cria
6. Home Assistant integration: https://github.com/ruifern/homeassistant-vikunja
7. Community Vikunja MCP reference: https://github.com/democratize-technology/vikunja-mcp-server

## Patterns we incorporated into this repository

1. Hybrid filtering fallback for task listing.
- Why: community MCP implementations highlight mixed server/client filtering when API filter behavior differs by deployment/version.
- What changed: `vikunja_list_tasks` now retries without server filter on validation failures and applies client-side filtering for ergonomic fields.
- Files:
  - `src/vikunja_mcp/tools/list_tasks.py`

2. Pagination with explicit memory guardrails.
- Why: workflow platforms and MCP integrations run better with predictable fetch bounds.
- What changed: `VikunjaClient.list_tasks()` now paginates and caps total fetched tasks via `VIKUNJA_MAX_PAGE_SIZE` and `VIKUNJA_MAX_FETCH_TASKS`.
- Files:
  - `src/vikunja_mcp/vikunja_client.py`
  - `src/vikunja_mcp/config.py`
  - `.env.example`

3. Migration bootstrap script inspired by `tw2vikunja`.
- Why: migration from existing task ledgers reduces adoption friction for real projects.
- What changed: added `scripts/import_taskwarrior_json.py` to import Taskwarrior-style JSON with idempotent `source_ref` keys.
- Files:
  - `scripts/import_taskwarrior_json.py`

## Intentionally deferred

1. Webhook receivers and event-stream processing.
- Rationale: it adds an always-on runtime surface and operational complexity; not required for deterministic local-first orchestration v1.

2. Attachment upload binaries.
- Rationale: path references are sufficient for first iteration and avoid credential/storage complexity.
