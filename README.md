# CueAPI Python SDK

The official Python SDK for [CueAPI](https://cueapi.ai) — scheduling infrastructure for agents.

## Install

```bash
pip install cueapi-sdk
```

## Quickstart

```python
from cueapi import CueAPI

client = CueAPI("cue_sk_your_key")
cue = client.cues.create(
    name="daily-report",
    cron="0 9 * * *",
    callback="https://my-app.com/webhook",
    payload={"task": "generate_report"},
)
print(f"Next run: {cue.next_run}")
```

## Why CueAPI?

- **Replace fragile cron jobs** — managed scheduling with automatic retries, execution logs, and failure alerts. No servers to maintain.
- **Built for AI agents** — schedule agent tasks, coordinate multi-agent pipelines, and retry failed workflows with exponential backoff.
- **Two transport modes** — webhook delivery to your public URL, or worker pull for agents behind firewalls.

## Transport Modes

### Webhook

CueAPI POSTs a signed payload to your callback URL when a cue fires:

```python
cue = client.cues.create(
    name="webhook-task",
    cron="0 9 * * *",
    callback="https://my-app.com/webhook",
    payload={"action": "sync"},
)
```

### Worker

Your local daemon polls CueAPI for executions. No public URL needed:

```python
cue = client.cues.create(
    name="worker-task",
    cron="0 */6 * * *",
    transport="worker",
    payload={"pipeline": "etl"},
)
```

Install the worker: `pip install cueapi-worker`

## Method Reference

### `CueAPI(api_key, *, base_url, timeout)`

Create a client. `api_key` starts with `cue_sk_`.

### `client.cues.create(...)`

| Parameter | Type | Description |
|---|---|---|
| `name` | `str` | **Required.** Unique name for the cue. |
| `cron` | `str` | Cron expression for recurring schedules. |
| `at` | `str \| datetime` | ISO 8601 datetime for one-time schedules. |
| `timezone` | `str` | IANA timezone (default `"UTC"`). |
| `callback` | `str` | Webhook URL for execution delivery. |
| `transport` | `str` | `"webhook"` (default) or `"worker"`. |
| `payload` | `dict` | JSON payload included in each execution. |
| `description` | `str` | Optional description. |
| `retry` | `dict` | `{"max_attempts": 3, "backoff_minutes": [1, 5, 15]}` |
| `on_failure` | `dict` | `{"email": true, "webhook": null, "pause": false}` |

Returns a `Cue` object.

### `client.cues.list(*, limit, offset, status)`

Returns a `CueList` with `.cues`, `.total`, `.limit`, `.offset`.

### `client.cues.get(cue_id)`

Returns a `Cue` object.

### `client.cues.update(cue_id, **fields)`

Update any field. Only provided fields are changed.

### `client.cues.pause(cue_id)`

Pause a cue. Returns the updated `Cue`.

### `client.cues.resume(cue_id)`

Resume a paused cue. Returns the updated `Cue`.

### `client.cues.delete(cue_id)`

Delete a cue. Returns `None`.

## Webhook Verification

Verify incoming webhook signatures in your handler:

```python
from cueapi import verify_webhook

is_valid = verify_webhook(
    payload=request.body,
    signature=request.headers["X-CueAPI-Signature"],
    timestamp=request.headers["X-CueAPI-Timestamp"],
    secret="whsec_your_secret",
)
```

## Error Handling

```python
from cueapi import CueAPI, AuthenticationError, RateLimitError, CueNotFoundError

try:
    cue = client.cues.get("cue_abc123")
except CueNotFoundError:
    print("Cue not found")
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
```

| Exception | HTTP Status | When |
|---|---|---|
| `AuthenticationError` | 401 | Invalid or missing API key |
| `CueLimitExceededError` | 403 | Plan cue limit reached |
| `CueNotFoundError` | 404 | Cue ID doesn't exist |
| `InvalidScheduleError` | 400/422 | Bad cron expression or request body |
| `RateLimitError` | 429 | Too many requests |
| `CueAPIServerError` | 5xx | Server error |

## Links

- [Documentation](https://docs.cueapi.ai)
- [API Reference](https://docs.cueapi.ai/api-reference/overview/)
- [Dashboard](https://dashboard.cueapi.ai)
- [CueAPI](https://cueapi.ai)
