# AGENTS

> Governance Hub for this project. Read this file first in every new session.

## Mission
LINE × n8n 供應商報價搜尋系統。

## Always-On Rules
- Keep this file concise: governance only; move details to spoke modules.
- Treat secrets and production credentials as strictly local and non-committable.
- Prioritize high-risk constraints and validation steps before implementation.
- If requirement is unclear and risk is non-trivial, mark as `NEED_REVIEW` instead of guessing.

## Default Execution Flow
1. Read `AGENTS.md` (this file).
2. Open only the relevant spoke modules from the quick map.
3. For large directories, read their `INDEX.md` first, then drill down minimally.
4. After work, update `agent-progress.md` and keep governance docs aligned.

## Quick Map
| Spoke | Path | When to Read |
|---|---|---|
| Context | `agent-context.md` | Project purpose, stack, boundaries, key paths. |
| Operations | `agent-operations.md` | High-impact rules, execution order, validation baseline. |
| Progress | `agent-progress.md` | Recent work, TODOs, unresolved items. |
| Refactor Report | `agent-refactor-report.md` | Phase 1+2 governance refactor record and metrics. |
| Legacy Archive | `agent-legacy-archive.md` | Full pre-refactor AGENTS content for audit/rollback. |
| Spoke Index: scripts | `scripts/INDEX.md` | High token-cost directory map. Read before opening raw files. |

## Known Disabled Features
- **`sync-sheets.yml`**（GitHub Actions）：已加 `if: false` 停用。
  Workflow 自 2026-03-19 後持續 failure，`quotations.json` 未再更新。
  如需重啟同步，請先修復 Service Account Secret 後移除 `if: false`。

## Escalation & Review
- `NEED_REVIEW`: conflicting specs, missing credentials, or potentially destructive changes.
- Keep historical details out of this hub; store them in spoke modules or legacy archive.
