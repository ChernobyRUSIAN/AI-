# Release Checklist

Use this checklist before shipping a Vuls v1.0 MVP release.

## Scope

- Milestone 1 through Milestone 11 commits are present.
- No work from future milestones is included.
- Architecture and implementation documents are not accidentally staged unless explicitly requested.
- The release supports the Telegram-first MVP path: idea intake, memory, template selection, LLM generation, ZIP export and GitHub export.

## Configuration

- `APP_ENV` is set to `staging` or `production`.
- `APP_BASE_URL` points to the public HTTPS endpoint.
- `TELEGRAM_WEBHOOK_SECRET` is unique per environment.
- `TELEGRAM_BOT_TOKEN` is valid and stored only as a secret.
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` and `SUPABASE_STORAGE_BUCKET` point to the intended environment.
- `OPENAI_API_KEY` and `OPENAI_MODEL` are configured.
- `GITHUB_TOKEN`, `GITHUB_OWNER` and `GITHUB_DEFAULT_PRIVATE` are configured.
- `PROJECT_WORKDIR` and artifact storage paths are writable by the service.
- `ZIP_MAX_BYTES` matches the release budget.

## Security

- No secrets are committed to Git.
- Supabase service role key is not exposed to clients or logs.
- Telegram webhook rejects invalid secrets.
- GitHub repository names are validated before API calls.
- LLM failures return user-safe Telegram messages without provider details.
- Generated file paths are validated before workspace writes and ZIP packaging.

## Validation

Run:

```bash
python -m pytest
python -m ruff check .
python -m mypy src
```

Confirm the E2E MVP tests pass:

```bash
python -m pytest tests/integration/test_vuls_v1_e2e_zip.py tests/integration/test_vuls_v1_e2e_github.py
```

Manual smoke test:

- Send `/start` in Telegram.
- Send `/new Create a CRM for a coffee shop with customers and orders`.
- Confirm the selected template is CRM.
- Trigger ZIP export and verify the ZIP artifact is created.
- Trigger GitHub export in a test repository owner and verify the repository URL is returned.
- Run `/projects` and `/status` and confirm the active project is visible.

## Release Decision

Release can proceed only when:

- All automated checks pass.
- E2E ZIP and GitHub paths pass with mocked providers.
- A staging smoke test passes with real Telegram, Supabase, OpenAI and GitHub credentials.
- Known limitations are documented for the release owner.
- Rollback path is clear: disable Telegram webhook, keep generated artifacts, and preserve Supabase records for audit.
