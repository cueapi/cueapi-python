# Changelog

All notable changes to cueapi-sdk will be documented here.

## [Unreleased]

### Added

- `client.cues.bulk_delete(ids)` — delete up to 100 cues in a single call. Returns `{"deleted": [...], "skipped": [...]}`. Per-ID atomic, not batch atomic. Sends `X-Confirm-Destructive: true` header automatically. Wraps `POST /v1/cues/bulk-delete` (cueapi #650). Parity port of cueapi-cli #46. Raises `ValueError` client-side on empty list or > 100 IDs.

## [0.2.0] - 2026-05-01

### Added
- `client.cues.fire(cue_id, payload_override=None, merge_strategy=None)` for ad-hoc one-shot triggers and for using cues as a messaging channel between agents. Wraps `POST /v1/cues/{id}/fire`.
- `client.executions.list_claimable(task=None, agent=None)` for unclaimed worker-transport executions ready for processing. Filters server-side via task / agent query params; required for single-purpose workers.
- `client.executions.claim(execution_id, worker_id=...)` for atomic claim of a specific execution. Returns 409 if already claimed.
- `client.executions.claim_next(worker_id=..., task=None)` for the next available execution. Without task the server picks the oldest pending; with task the SDK fans out internally (list_claimable filtered, pick oldest, claim by ID) since the server's claim endpoint does not accept a task filter today.

### Changed
- `__version__` in `cueapi/__init__.py` had drifted to 0.1.2 while `pyproject.toml` was at 0.1.3. Both now aligned at 0.2.0.

### Pending follow-up
- `client.executions.heartbeat(execution_id)` currently sends an empty body and does NOT include `worker_id` via the `X-Worker-Id` request header that the server reads from. Worker-id is what the server uses to enforce ownership on the heartbeat (returns 403 on mismatch); without it the race-protection check is silently bypassed. A signature change to add `worker_id` is held pending technical review of the deprecation cadence.

## [0.1.0] - 2025-03-28

### Added
- Initial release of the official Python SDK for CueAPI
- CueAPI client with full cues CRUD (create, list, get, update, delete, pause, resume)
- Executions client (list, get)
- Webhook transport support
- Worker transport support via cueapi-worker
- Webhook signature verification (verify_webhook) using HMAC-SHA256
- Typed exceptions: AuthenticationError, CueLimitExceededError, CueNotFoundError, InvalidScheduleError, RateLimitError, CueAPIServerError
- Python 3.9+ support
- 40 tests via pytest
- Working examples: basic_usage.py, webhook_handler.py, worker_setup.py
