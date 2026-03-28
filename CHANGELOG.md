# Changelog

All notable changes to cueapi-sdk will be documented here.

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
