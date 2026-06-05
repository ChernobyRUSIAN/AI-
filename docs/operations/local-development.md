# Vuls Local Run Guide

This guide runs Vuls locally in the order an operator should set it up. It does not add product features; it documents the v1.0 MVP runtime and validation path.

Important current-state note: the checked-in v1.0 code has FastAPI/Telegram contracts and deterministic E2E validation for the full MVP chain. The public webhook route currently validates the Telegram secret and returns `ok`; a real live Telegram-to-generation smoke test requires the runtime project service adapter to be wired to the composed memory, template, LLM, generation and GitHub services.

## 1. Install Local Prerequisites

Required:

- Python 3.13
- Git
- Supabase CLI for local database work, or access to a hosted Supabase project
- A Telegram account
- An OpenAI platform account
- A GitHub account or organization where Vuls may create repositories

Install Python dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Create local runtime folders:

```powershell
New-Item -ItemType Directory -Force var\projects
New-Item -ItemType Directory -Force var\artifacts
```

## 2. Create `.env`

Copy the example file:

```powershell
Copy-Item .env.example .env
```

Fill every required variable:

```env
APP_ENV=local
APP_BASE_URL=http://localhost:8000
APP_SECRET_KEY=change-me-local-secret

TELEGRAM_BOT_TOKEN=123456:replace-with-bot-token
TELEGRAM_WEBHOOK_SECRET=replace-with-webhook-secret

SUPABASE_URL=https://example.supabase.co
SUPABASE_SERVICE_ROLE_KEY=replace-with-server-only-secret-or-service-role-key
SUPABASE_STORAGE_BUCKET=vuls-artifacts

OPENAI_API_KEY=replace-with-openai-api-key
OPENAI_MODEL=gpt-5.1

GITHUB_TOKEN=replace-with-github-token
GITHUB_OWNER=replace-with-github-owner
GITHUB_DEFAULT_PRIVATE=true

PROJECT_WORKDIR=./var/projects
ZIP_MAX_BYTES=25000000
LOG_LEVEL=INFO
SENTRY_DSN=
OPENAI_TIMEOUT_SECONDS=60
GITHUB_API_BASE_URL=https://api.github.com
RATE_LIMIT_PROJECTS_PER_USER_DAY=5
RATE_LIMIT_LLM_CALLS_PER_PROJECT=8
```

Security rules:

- Do not commit `.env`.
- Treat `TELEGRAM_BOT_TOKEN`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY` and `GITHUB_TOKEN` as server-only secrets.
- Prefer a Supabase `sb_secret_...` key where compatible; Supabase still exposes legacy `service_role` keys, but secret keys are the safer backend option.

## 3. Telegram Setup

1. Open Telegram and start `@BotFather`.
2. Run `/newbot`.
3. Choose the display name, for example `Vuls`.
4. Choose a unique bot username ending in `bot`, for example `vuls_local_bot`.
5. Copy the token into `TELEGRAM_BOT_TOKEN`.
6. Set bot commands in BotFather:

```text
start - Start Vuls
new - Create a new product project
projects - Show recent projects
status - Show active project status
```

For webhook testing, expose the local FastAPI server through an HTTPS tunnel and update `APP_BASE_URL` to that public URL.

Set webhook:

```powershell
$env:TELEGRAM_BOT_TOKEN = "<token>"
$env:APP_BASE_URL = "https://your-public-tunnel.example"
$env:TELEGRAM_WEBHOOK_SECRET = "<secret>"
Invoke-RestMethod -Method Post `
  -Uri "https://api.telegram.org/bot$env:TELEGRAM_BOT_TOKEN/setWebhook" `
  -Body @{ url = "$env:APP_BASE_URL/webhooks/telegram/$env:TELEGRAM_WEBHOOK_SECRET" }
```

Check webhook:

```powershell
Invoke-RestMethod -Uri "https://api.telegram.org/bot$env:TELEGRAM_BOT_TOKEN/getWebhookInfo"
```

Delete webhook when you stop local development:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "https://api.telegram.org/bot$env:TELEGRAM_BOT_TOKEN/deleteWebhook"
```

## 4. Supabase Setup

Hosted Supabase:

1. Create or open a Supabase project.
2. Copy the Project URL into `SUPABASE_URL`.
3. Copy the backend secret key or legacy service role key into `SUPABASE_SERVICE_ROLE_KEY`.
4. Create a storage bucket named `vuls-artifacts`.
5. Apply the database schema from:

```text
supabase/migrations/20260602024549_init_vuls_v1.sql
```

Local Supabase CLI path:

```powershell
supabase start
supabase db reset
```

Then use the local API URL and service role key printed by the Supabase CLI in `.env`.

## 5. OpenAI Setup

1. Create an OpenAI API key in the OpenAI platform dashboard.
2. Put the key into `OPENAI_API_KEY`.
3. Set `OPENAI_MODEL` to a model available to your account. Keep `gpt-5.1` only if your account has access to it.
4. Keep `OPENAI_TIMEOUT_SECONDS=60` for local testing unless provider latency requires a larger timeout.

Quick local sanity check:

```powershell
python -m pytest tests\unit\llm\test_structured_generation.py
```

The unit tests use mocked responses and do not spend API credits.

## 6. GitHub Setup

1. Create a token for the account or organization in `GITHUB_OWNER`.
2. For classic PATs, use `repo` for private repositories or `public_repo` for public-only testing.
3. For fine-grained tokens, grant:
   - `Administration: write` for repository creation.
   - `Contents: write` for committing generated files.
4. Put the token into `GITHUB_TOKEN`.
5. Put the target user or organization into `GITHUB_OWNER`.
6. Keep `GITHUB_DEFAULT_PRIVATE=true` for MVP testing unless you intentionally want public generated repos.

Quick local sanity check:

```powershell
python -m pytest tests\unit\github\test_github_service.py tests\integration\test_github_export_flow.py
```

The tests use fake GitHub clients and do not create real repositories.

## 7. Start Vuls Locally

Run the FastAPI contract server:

```powershell
python -m uvicorn vuls.api.app:create_api_app --factory --host 0.0.0.0 --port 8000
```

Health check:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected shape:

```json
{
  "status": "ok",
  "version": "v1.0"
}
```

Webhook contract check with the configured secret:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/webhooks/telegram/replace-with-webhook-secret" `
  -ContentType "application/json" `
  -Body '{"update_id":1,"message":{"message_id":1,"text":"/start"}}'
```

Expected response:

```json
{ "ok": true }
```

Invalid secret check:

```powershell
Invoke-WebRequest -Method Post `
  -Uri "http://localhost:8000/webhooks/telegram/wrong-secret" `
  -ContentType "application/json" `
  -Body '{"update_id":1}'
```

Expected result: HTTP `403`.

## 8. Run Deterministic MVP E2E Validation

This is the first complete local E2E check available in the repository today. It validates Telegram-style input through memory, template selection, mocked LLM gateway, project generation, ZIP export and fake GitHub export.

```powershell
python -m pytest tests\integration\test_vuls_v1_e2e_zip.py tests\integration\test_vuls_v1_e2e_github.py
```

Expected result:

```text
4 passed
```

Full local verification:

```powershell
python -m pytest
python -m ruff check .
python -m mypy src
```

## 9. First Manual End-to-End Scenario

Use this after the runtime project service adapter is wired to real Supabase, OpenAI and GitHub services.

1. Start the API server:

```powershell
python -m uvicorn vuls.api.app:create_api_app --factory --host 0.0.0.0 --port 8000
```

2. Start an HTTPS tunnel to `localhost:8000`.
3. Set Telegram webhook to:

```text
https://your-public-tunnel.example/webhooks/telegram/<TELEGRAM_WEBHOOK_SECRET>
```

4. Open the bot in Telegram.
5. Send:

```text
/start
```

Expected: Vuls welcome message and main actions.

6. Send:

```text
/new Create a CRM for a coffee shop with customers, orders and staff tasks
```

Expected:

- user and project memory are created;
- CRM template is selected;
- Vuls returns the project brief or generation options.

7. Choose ZIP export.

Expected:

- LLM gateway returns a structured project manifest;
- project files are written under `PROJECT_WORKDIR`;
- ZIP artifact is created;
- Telegram returns a ZIP artifact reference.

8. Start a second project or repeat the same scenario choosing GitHub export.

Expected:

- GitHub repository is created under `GITHUB_OWNER`;
- generated files are committed serially;
- Telegram returns the repository URL.

9. Send:

```text
/projects
```

Expected: the recent project list includes the generated project.

10. Send:

```text
/status
```

Expected: active project status shows `completed`, selected template and export URL or ZIP artifact.

## 10. Troubleshooting Order

1. `python -m pytest tests\integration\test_vuls_v1_e2e_zip.py tests\integration\test_vuls_v1_e2e_github.py`
2. `Invoke-RestMethod http://localhost:8000/health`
3. Telegram `getWebhookInfo`
4. Supabase project URL and secret key
5. OpenAI key and model access
6. GitHub token permissions and owner
7. `PROJECT_WORKDIR` write permissions

## References

- Telegram BotFather and bot command setup: https://core.telegram.org/bots/features
- Telegram Bot API webhooks: https://core.telegram.org/bots/api#setwebhook
- Supabase API keys: https://supabase.com/docs/guides/getting-started/api-keys
- Supabase local development: https://supabase.com/docs/guides/local-development
- OpenAI API quickstart: https://developers.openai.com/api/docs/quickstart
- OpenAI API key safety: https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety
- GitHub repository API: https://docs.github.com/en/rest/repos/repos
- GitHub contents API: https://docs.github.com/en/rest/repos/contents
