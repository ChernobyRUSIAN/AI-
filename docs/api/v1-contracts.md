# Vuls API Contracts v1.0

## Health

`GET /health`

```json
{
  "status": "ok",
  "version": "v1.0",
  "dependencies": {
    "supabase": "ok",
    "openai": "not_checked",
    "github": "not_checked"
  }
}
```

## Telegram Webhook

`POST /webhooks/telegram/{secret}`

Invalid secret response:

```json
{
  "error": {
    "code": "invalid_webhook_secret",
    "message": "Invalid Telegram webhook secret"
  }
}
```

Valid secret response:

```json
{
  "ok": true
}
```

## Create Project

`POST /internal/projects`

Request:

```json
{
  "telegram_user_id": 123456789,
  "telegram_chat_id": 123456789,
  "idea": "Create a CRM for a small coffee shop",
  "language_code": "en"
}
```

Response:

```json
{
  "project_id": "11111111-1111-1111-1111-111111111111",
  "status": "clarifying",
  "next_message": "Who will use this CRM?"
}
```

## Generate Project

`POST /internal/projects/{project_id}/generate`

Request:

```json
{
  "answers": {
    "target_users": "owner and staff",
    "must_have_features": ["customers", "orders", "tasks"]
  },
  "export": "github"
}
```

Response:

```json
{
  "project_id": "11111111-1111-1111-1111-111111111111",
  "status": "completed",
  "template": "crm",
  "github_url": "https://github.com/example/vuls-coffee-crm",
  "zip_artifact_id": null
}
```

## Project Status

`GET /internal/projects/{project_id}`

```json
{
  "project_id": "11111111-1111-1111-1111-111111111111",
  "title": "Coffee CRM",
  "status": "completed",
  "selected_template_key": "crm",
  "repository_url": "https://github.com/example/vuls-coffee-crm",
  "updated_at": "2026-06-01T18:00:00Z"
}
```
