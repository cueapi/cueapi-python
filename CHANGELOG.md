# Changelog

All notable changes to cueapi-sdk will be documented here.

## [Unreleased]

### Added

- **`client.cues.fire(auto_verify=True)` body-verify mirror (Mike body-verify directive 2026-05-11).** Parallel to `MessagesResource.send` auto_verify. Default verify-on. Sends `X-CueAPI-Verify-Echo: true` request header; substrate echoes received body bytes under `body_received` (str) + SHA256 hex under `body_received_sha256`. SDK computes sha256 of canonical request body + compares hex equality (constant-cost verify path), falling back to full string compare on hash mismatch. On drift raises `BodyVerifyMismatchError` with diagnostic attributes including `message_id` (= execution_id for fire). `auto_verify=False` opts out. Backward-compat: pre-Layer-1 substrate omits the echo fields → no-op + success. Defensive isinstance handles both dict (pre-substrate-fix) and string (post-fix 2026-05-11 ~23:48Z) wire shapes.
- **`client.messages.send(auto_verify=True)` body-verify defense (Mike directive 2026-05-11).** New `auto_verify` kwarg, default `True`. When set, the SDK sends `X-CueAPI-Verify-Echo: true` request header. Substrate-side (Phase 1; cueapi-core's lane) echoes the body it received back in the response under `body_received`. SDK diffs sent vs received and raises `BodyVerifyMismatchError` on drift (with `sent_body`, `received_body`, `first_divergence_byte`, `message_id` attributes for programmatic recovery / diagnostic output). Catches the caller-side shell-expansion bug class where `body=f"... {dynamic_var} ..."` or worse `body=os.popen(...)` silently mutated body content upstream. Opt-out via `auto_verify=False` for perf-sensitive flows. Backward-compat: SDK no-ops when substrate omits the echo field (pre-Layer-1 behavior unchanged). New helper: `cueapi.exceptions.first_divergence_byte(a, b)` returns the byte index of the first differing position (pure function; re-usable cross-SDK).
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
