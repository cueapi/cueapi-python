> **For AI agents:** This is the official Python SDK for CueAPI. Run `pip install cueapi-sdk`. Your API key is in `CUEAPI_API_KEY`. Create a client: `client = CueAPI(os.environ["CUEAPI_API_KEY"])`. Schedule a task: `client.cues.create(name="task-name", cron="0 9 * * *", callback="https://your-handler.com", payload={})`. For agents without a public URL: set `transport="worker"` and run `pip install cueapi-worker`, then define a handler with `@worker.handler("task-name")` returning `{"status": "success"}` or `{"status": "failure", "error": "reason"}`. List executions: `client.executions.list()`. Get one: `client.executions.get("exec_id")`. Do not retry on `AuthenticationError` or `CueLimitExceededError`. Wait `e.retry_after` seconds on `RateLimitError`.

# cueapi-sdk

Your agents are failing silently. CueAPI tells you when and why.

**Cron has no concept of success. Cue does.**

[![PyPI version](https://img.shields.io/pypi/v/cueapi-sdk?label=pypi)](https://pypi.org/project/cueapi-sdk/)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://pypi.org/project/cueapi-sdk/)
[![License](https://img.shields.io/badge/license-MIT-black)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-40%20passing-brightgreen)](.github/workflows)
[![Docs](https://img.shields.io/badge/docs-docs.cueapi.ai-black)](https://docs.cueapi.ai)

The official Python SDK for [CueAPI](https://cueapi.ai). Open source execution accountability for AI agents.

---

## Install

```bash
pip install cueapi-sdk
```

---

## Quickstart

```python
from cueapi import CueAPI

client = CueAPI("cue_sk_your_key")

# Schedule an agent to run every morning
cue = client.cues.create(
    name="morning-agent-brief",
    cron="0 9 * * *",
    timezone="America/Los_Angeles",
    callback="https://your-agent.com/run",
    payload={"task": "daily_brief"},
)

print(f"Scheduled. Next run: {cue.next_run}")
# Scheduled. Next run: 2026-03-28T09:00:00-08:00
```

---

## Why CueAPI over cron?

Your agent ran at 3am. Did it succeed? Cron does not know.

CueAPI tracks every execution separately from delivery, so you always know what happened.

```python
# Check what actually happened
execution = client.executions.get("exec_01HX...")
print(execution.outcome)      # "success" or "failure" -- reported by your handler
print(execution.attempts)     # 1 (or 2, 3 if it had to retry)
print(execution.delivered_at) # exactly when it was delivered
print(execution.status)       # "delivered", "failed", "retrying"
```

**What you get that cron cannot give you:**

- Execution history with outcome tracking
- Automatic retries with exponential backoff (1, 5, 15 min)
- Email + webhook alerts when all retries exhaust
- Worker transport with no public URL needed
- Signed webhook payloads

---

## Two transport modes

### Webhook (default)

CueAPI POSTs a signed payload to your URL when a cue fires:

```python
cue = client.cues.create(
    name="data-sync",
    cron="0 */6 * * *",
    callback="https://your-app.com/webhook",
    payload={"pipeline": "sync"},
)
```

Your handler receives the payload, processes it, and CueAPI records the outcome.

### Worker (no public URL needed)

For agents running locally, in private networks, or behind firewalls. Your daemon polls CueAPI instead of waiting for inbound requests.

```bash
pip install cueapi-worker
```

```python
from cueapi_worker import Worker

worker = Worker(api_key="cue_sk_your_key")

@worker.handler("run-agent")
def handle(payload):
    result = run_my_agent(payload["task"])
    return {"status": "success", "summary": result}

worker.start()  # polls continuously, no inbound firewall rules needed
```

Create the cue with `transport="worker"`:

```python
cue = client.cues.create(
    name="nightly-pipeline",
    cron="0 2 * * *",
    transport="worker",
    payload={"pipeline": "etl"},
)
```

---

## Webhook verification

Always verify incoming webhook signatures before processing:

```python
from cueapi import verify_webhook

@app.post("/webhook")
def handle_cue(request: Request):
    is_valid = verify_webhook(
        payload=request.body,
        signature=request.headers["X-CueAPI-Signature"],
        timestamp=request.headers["X-CueAPI-Timestamp"],
        secret="whsec_your_secret",
        tolerance=300,  # seconds, default
    )

    if not is_valid:
        return {"error": "invalid signature"}, 401

    data = request.json()
    run_task(data["payload"])
    return {"outcome": "success"}
```

Signatures use HMAC-SHA256 in `v1={hex}` format. The `tolerance` parameter rejects replayed requests older than 5 minutes.

---

## Error handling

```python
from cueapi import (
    CueAPI,
    AuthenticationError,
    CueLimitExceededError,
    CueNotFoundError,
    InvalidScheduleError,
    RateLimitError,
    CueAPIServerError,
)

try:
    cue = client.cues.create(
        name="my-agent",
        cron="0 9 * * *",
        callback="https://example.com/run",
    )
except CueLimitExceededError:
    print("Plan limit reached. Upgrade at cueapi.ai")
except InvalidScheduleError as e:
    print(f"Bad cron expression: {e}")
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except CueAPIServerError:
    print("Server error. CueAPI status at status.cueapi.ai")
```

| Exception | HTTP | When |
|---|---|---|
| `AuthenticationError` | 401 | Invalid or missing API key |
| `CueLimitExceededError` | 403 | Plan cue limit reached |
| `CueNotFoundError` | 404 | Cue ID does not exist |
| `InvalidScheduleError` | 400/422 | Bad cron expression or request body |
| `RateLimitError` | 429 | Too many requests |
| `CueAPIServerError` | 5xx | Server error |

---

## Full method reference

### `CueAPI(api_key, *, base_url, timeout)`

```python
client = CueAPI(
    api_key="cue_sk_...",               # or set CUEAPI_API_KEY env var
    base_url="https://api.cueapi.ai",   # default
    timeout=30,                         # seconds, default
)
```

### `client.cues.create(**fields)`

| Parameter | Type | Description |
|---|---|---|
| `name` | `str` | Required. Unique name. |
| `cron` | `str` | Cron expression for recurring schedules. |
| `at` | `str or datetime` | ISO 8601 for one-time schedules. |
| `timezone` | `str` | IANA timezone (default `"UTC"`). |
| `callback` | `str` | Webhook URL (required if `transport="webhook"`). |
| `transport` | `str` | `"webhook"` (default) or `"worker"`. |
| `payload` | `dict` | JSON payload included in each execution. |
| `description` | `str` | Optional description. |
| `retry` | `dict` | `{"max_attempts": 3, "backoff_minutes": [1, 5, 15]}` |
| `on_failure` | `dict` | `{"email": true, "webhook": null, "pause": false}` |

Returns a `Cue` object.

### Other cue methods

```python
client.cues.list(limit=20, offset=0, status="active")  # CueList
client.cues.get("cue_abc123")                           # Cue
client.cues.update("cue_abc123", cron="0 10 * * *")    # Cue
client.cues.pause("cue_abc123")                        # Cue
client.cues.resume("cue_abc123")                       # Cue
client.cues.delete("cue_abc123")                       # None
```

### Executions

```python
client.executions.list(cue_id="cue_abc123", limit=20)  # ExecutionList
client.executions.get("exec_01HX...")                  # Execution
```

---

## Examples

See [`/examples`](examples/) for working code:

- [`basic_usage.py`](examples/basic_usage.py) - create, list, pause, delete cues
- [`webhook_handler.py`](examples/webhook_handler.py) - FastAPI handler with signature verification
- [`worker_setup.py`](examples/worker_setup.py) - worker daemon for private network agents

---

## Links

- [Dashboard](https://dashboard.cueapi.ai) - manage cues and view executions
- [Documentation](https://docs.cueapi.ai) - full guides and API reference
- [API Reference](https://docs.cueapi.ai/api-reference/overview) - all endpoints
- [cueapi-core](https://github.com/cueapi/cueapi-core) - open source server
- [cueapi.ai](https://cueapi.ai) - hosted service, free tier available
- [Changelog](CHANGELOG.md) - full version history

---

## License

MIT. See [LICENSE](LICENSE).

---

*Built by [Vector Apps](https://cueapi.ai/about)*
