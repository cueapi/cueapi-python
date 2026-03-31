# CLAUDE.md - Rules for AI agents working on this repo

## Branch protection
- Never bypass branch protection or force merge failing checks
- Never use --no-verify or skip pre-commit hooks
- All changes to main must pass required status checks (sdk-integration, staging-integration)
- If a check fails, fix the root cause before merging

## Publishing
- PyPI publish triggers only on version tags (v*)
- Uses trusted publishing (OIDC) - no API tokens
- Never store PYPI_TOKEN in source or secrets

## Security
- Never hardcode API keys, secrets, or tokens in source code
- Use environment variables or GitHub secrets for all credentials
- All GitHub Actions must be pinned to commit SHAs, not version tags
- Staging keys go in CUEAPI_STAGING_API_KEY GitHub secret, never in code

## Code quality
- Run tests locally before pushing: pytest tests/ -v
- Do not use em dashes in any user-facing content
