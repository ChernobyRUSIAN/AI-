# Vuls v1.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Vuls v1.0 as a Telegram-first AI Product Builder that turns a user idea into a generated project delivered as a ZIP file or GitHub repository.

**Architecture:** Vuls v1.0 is a Python 3.13 modular monolith with FastAPI for HTTP/webhook APIs, aiogram for Telegram bot handling, Supabase for persistence, OpenAI for generation, and GitHub API for repository export. The MVP deliberately excludes Hermes, Open Design, Playwright, sandbox execution, code interpreter execution, and deployment automation from the required path.

**Tech Stack:** Python 3.13, FastAPI, aiogram, Pydantic v2, Supabase Python client/PostgREST, OpenAI Python SDK, GitHub REST API, pytest, ruff, mypy, Docker for local app packaging only.

---

## 1. Scope Guardrails

Implementation must not start until this plan is approved.

Vuls v1.0 includes:

- Telegram intake and status flow.
- Supabase schema and repository layer.
- OpenAI/LLM generation gateway.
- Template System with CRM, SaaS, Marketplace, AI Agent and Dashboard templates.
- Memory Layer with User, Project, Conversation and Knowledge memory.
- ZIP export.
- GitHub repository export.
- Basic admin/internal HTTP contracts through FastAPI.

Vuls v1.0 excludes:

- Hermes Agent execution.
- Open Design execution.
- Playwright browser automation.
- Sandbox execution pool.
- Code Interpreter execution.
- automatic deployment/preview hosting.
- billing UI.
- production web dashboard.

## 2. Repository Structure

Planned repository root after v1.0 implementation:

```text
Vols/
  README.md
  pyproject.toml
  uv.lock
  .env.example
  .gitignore
  docker-compose.yml
  Dockerfile
  alembic.ini
  docs/
    superpowers/
      specs/
        2026-06-01-vuls-architecture-design.md
      plans/
        2026-06-01-vuls-v1-implementation-plan.md
    api/
      v1-contracts.md
    operations/
      local-development.md
      release-checklist.md
  src/
    vuls/
      __init__.py
      main.py
      api/
        __init__.py
        app.py
        dependencies.py
        routes/
          __init__.py
          health.py
          telegram.py
          projects.py
          internal.py
      bot/
        __init__.py
        app.py
        dispatcher.py
        handlers/
          __init__.py
          start.py
          new_project.py
          projects.py
          status.py
          callbacks.py
        keyboards.py
        messages.py
      core/
        __init__.py
        config.py
        errors.py
        logging.py
        security.py
        time.py
      db/
        __init__.py
        client.py
        models.py
        repositories/
          __init__.py
          users.py
          projects.py
          memory.py
          templates.py
          artifacts.py
          audit.py
      llm/
        __init__.py
        gateway.py
        openai_client.py
        prompts.py
        schemas.py
        safety.py
      github/
        __init__.py
        client.py
        service.py
        schemas.py
      generation/
        __init__.py
        orchestrator.py
        project_builder.py
        zip_exporter.py
        file_manifest.py
      memory/
        __init__.py
        service.py
        summarizer.py
        schemas.py
      templates/
        __init__.py
        registry.py
        renderer.py
        schemas.py
        catalog/
          crm/
            template.yaml
            prompts.md
            files.yaml
          saas/
            template.yaml
            prompts.md
            files.yaml
          marketplace/
            template.yaml
            prompts.md
            files.yaml
          ai_agent/
            template.yaml
            prompts.md
            files.yaml
          dashboard/
            template.yaml
            prompts.md
            files.yaml
      i18n/
        __init__.py
        locales/
          ru.json
          en.json
          es.json
          de.json
          fr.json
          pt.json
          it.json
          tr.json
          ar.json
          zh.json
          ja.json
          ko.json
  supabase/
    config.toml
    migrations/
      generated_by_supabase_cli_init_vuls_v1.sql
  tests/
    unit/
      api/
      bot/
      db/
      llm/
      generation/
      memory/
      templates/
    integration/
      test_telegram_intake_flow.py
      test_project_generation_flow.py
      test_github_export_flow.py
    fixtures/
      telegram_update_start.json
      telegram_update_new_project.json
      template_catalog.json
```

Notes:

- The migration filename shown above is descriptive only. During implementation, create the migration with `supabase migration new init_vuls_v1`; use the CLI-generated filename.
- `src/vuls/templates/catalog/*` stores template definitions, not generated user projects.
- Generated project workspaces must be temporary runtime directories, not committed into this repository.

## 3. Folder Structure and Responsibilities

| Folder | Responsibility |
| --- | --- |
| `src/vuls/api` | FastAPI app factory, HTTP routes, dependency injection, webhook endpoint |
| `src/vuls/bot` | aiogram dispatcher, Telegram command handlers, callbacks, user-facing messages |
| `src/vuls/core` | configuration, logging, errors, security utilities, shared primitives |
| `src/vuls/db` | Supabase client and repository boundaries for persistent data |
| `src/vuls/llm` | OpenAI adapter, prompt assembly, structured output schemas, safety checks |
| `src/vuls/github` | GitHub API client and repository export service |
| `src/vuls/generation` | project generation orchestration, file manifest assembly, ZIP export |
| `src/vuls/memory` | memory read/write, summarization, context assembly |
| `src/vuls/templates` | template registry, template metadata, prompt and file blueprint rendering |
| `src/vuls/i18n` | system message translations for Telegram and generated-app scaffolding |
| `supabase` | local Supabase config and migrations |
| `tests` | unit and integration tests for every module boundary |
| `docs/api` | API contracts visible to implementers |
| `docs/operations` | local development and release procedures |

## 4. Module Boundaries

### 4.1 API Boundary

FastAPI owns HTTP ingress only:

- health checks;
- Telegram webhook;
- internal project/status endpoints;
- request validation;
- mapping HTTP errors to response codes.

FastAPI must not contain generation logic, direct OpenAI calls or direct GitHub calls.

### 4.2 Bot Boundary

aiogram owns Telegram-specific interaction:

- `/start`;
- `/new`;
- `/projects`;
- `/status`;
- language selection;
- inline approval/cancel callbacks;
- outgoing messages.

Bot handlers call application services, not Supabase/OpenAI/GitHub clients directly.

### 4.3 Database Boundary

`src/vuls/db/repositories` owns all Supabase persistence calls. Other modules use repository methods and do not know table names except through repository contracts.

### 4.4 LLM Boundary

`src/vuls/llm` owns provider calls and structured generation:

- selected model;
- prompt rendering;
- JSON schema validation;
- token and usage recording;
- retry policy;
- safety pre-checks.

The rest of the app requests typed outputs such as `ProjectBrief`, `TemplateSelection` and `GeneratedProjectManifest`.

### 4.5 Generation Boundary

`src/vuls/generation` owns the v1.0 workflow:

1. read memory;
2. normalize brief;
3. select template;
4. generate file manifest;
5. validate manifest shape;
6. persist artifacts;
7. export ZIP or GitHub repo;
8. update project status.

### 4.6 Template Boundary

Templates are declarative. They must not call APIs directly. The template renderer reads metadata and creates prompt/file blueprint inputs for the generation service.

### 4.7 Memory Boundary

Memory service owns:

- loading user/project/conversation context before generation;
- writing durable decisions after every step;
- summarizing long conversations;
- separating raw messages from durable facts.

### 4.8 GitHub Boundary

GitHub service owns:

- repository creation;
- file commit creation;
- repository metadata persistence;
- error mapping for rate limits, auth failures and name conflicts.

## 5. Database Schema

Supabase must use Postgres with RLS enabled on exposed tables. v1.0 backend uses service role credentials only server-side. Telegram users are represented as application identities, not Supabase Auth users in the MVP.

### 5.1 Tables

#### `profiles`

| Column | Type | Constraints |
| --- | --- | --- |
| `id` | `uuid` | primary key, default `gen_random_uuid()` |
| `telegram_user_id` | `bigint` | unique, not null |
| `telegram_username` | `text` | nullable |
| `display_name` | `text` | nullable |
| `language_code` | `text` | not null, default `en` |
| `preferred_stack` | `jsonb` | not null, default `{}` |
| `created_at` | `timestamptz` | not null, default `now()` |
| `updated_at` | `timestamptz` | not null, default `now()` |

#### `telegram_chats`

| Column | Type | Constraints |
| --- | --- | --- |
| `id` | `uuid` | primary key |
| `profile_id` | `uuid` | references `profiles(id)` |
| `telegram_chat_id` | `bigint` | unique, not null |
| `chat_type` | `text` | not null |
| `last_seen_at` | `timestamptz` | not null |
| `created_at` | `timestamptz` | not null |

#### `projects`

| Column | Type | Constraints |
| --- | --- | --- |
| `id` | `uuid` | primary key |
| `owner_profile_id` | `uuid` | references `profiles(id)`, not null |
| `title` | `text` | not null |
| `slug` | `text` | not null |
| `status` | `text` | not null; values: `draft`, `clarifying`, `generating`, `exporting`, `completed`, `failed`, `cancelled` |
| `selected_template_key` | `text` | nullable |
| `brief` | `jsonb` | not null, default `{}` |
| `created_at` | `timestamptz` | not null |
| `updated_at` | `timestamptz` | not null |

#### `project_members`

| Column | Type | Constraints |
| --- | --- | --- |
| `project_id` | `uuid` | references `projects(id)`, primary key part |
| `profile_id` | `uuid` | references `profiles(id)`, primary key part |
| `role` | `text` | not null; values: `owner`, `editor`, `viewer` |
| `created_at` | `timestamptz` | not null |

#### `project_stages`

| Column | Type | Constraints |
| --- | --- | --- |
| `id` | `uuid` | primary key |
| `project_id` | `uuid` | references `projects(id)`, not null |
| `stage` | `text` | not null; values: `intake`, `clarification`, `template_selection`, `generation`, `export`, `completed` |
| `status` | `text` | not null; values: `pending`, `running`, `completed`, `failed`, `cancelled` |
| `input` | `jsonb` | not null, default `{}` |
| `output` | `jsonb` | not null, default `{}` |
| `error` | `jsonb` | nullable |
| `started_at` | `timestamptz` | nullable |
| `completed_at` | `timestamptz` | nullable |

#### `memory_items`

| Column | Type | Constraints |
| --- | --- | --- |
| `id` | `uuid` | primary key |
| `profile_id` | `uuid` | references `profiles(id)`, not null |
| `project_id` | `uuid` | references `projects(id)`, nullable |
| `memory_type` | `text` | not null; values: `user`, `project`, `conversation`, `knowledge` |
| `source` | `text` | not null; values: `telegram`, `generation`, `system`, `manual` |
| `content` | `jsonb` | not null |
| `summary` | `text` | not null |
| `confidence` | `numeric(3,2)` | not null, default `1.00` |
| `created_at` | `timestamptz` | not null |
| `updated_at` | `timestamptz` | not null |

#### `conversation_messages`

| Column | Type | Constraints |
| --- | --- | --- |
| `id` | `uuid` | primary key |
| `profile_id` | `uuid` | references `profiles(id)`, not null |
| `project_id` | `uuid` | references `projects(id)`, nullable |
| `telegram_message_id` | `bigint` | nullable |
| `direction` | `text` | not null; values: `inbound`, `outbound` |
| `message_type` | `text` | not null; values: `text`, `command`, `callback`, `document`, `system` |
| `text` | `text` | nullable |
| `payload` | `jsonb` | not null, default `{}` |
| `created_at` | `timestamptz` | not null |

#### `templates`

| Column | Type | Constraints |
| --- | --- | --- |
| `id` | `uuid` | primary key |
| `key` | `text` | unique, not null; values include `crm`, `saas`, `marketplace`, `ai_agent`, `dashboard` |
| `name` | `text` | not null |
| `description` | `text` | not null |
| `is_active` | `boolean` | not null, default `true` |
| `created_at` | `timestamptz` | not null |

#### `template_versions`

| Column | Type | Constraints |
| --- | --- | --- |
| `id` | `uuid` | primary key |
| `template_id` | `uuid` | references `templates(id)`, not null |
| `version` | `text` | not null |
| `manifest` | `jsonb` | not null |
| `created_at` | `timestamptz` | not null |

#### `generation_runs`

| Column | Type | Constraints |
| --- | --- | --- |
| `id` | `uuid` | primary key |
| `project_id` | `uuid` | references `projects(id)`, not null |
| `template_version_id` | `uuid` | references `template_versions(id)`, nullable |
| `status` | `text` | not null; values: `queued`, `running`, `completed`, `failed`, `cancelled` |
| `provider` | `text` | not null |
| `model` | `text` | not null |
| `input_summary` | `text` | not null |
| `output_manifest` | `jsonb` | nullable |
| `usage` | `jsonb` | not null, default `{}` |
| `error` | `jsonb` | nullable |
| `created_at` | `timestamptz` | not null |
| `completed_at` | `timestamptz` | nullable |

#### `artifacts`

| Column | Type | Constraints |
| --- | --- | --- |
| `id` | `uuid` | primary key |
| `project_id` | `uuid` | references `projects(id)`, not null |
| `generation_run_id` | `uuid` | references `generation_runs(id)`, nullable |
| `artifact_type` | `text` | not null; values: `manifest`, `zip`, `readme`, `source_snapshot`, `log` |
| `storage_path` | `text` | nullable |
| `content` | `jsonb` | nullable |
| `created_at` | `timestamptz` | not null |

#### `repositories`

| Column | Type | Constraints |
| --- | --- | --- |
| `id` | `uuid` | primary key |
| `project_id` | `uuid` | references `projects(id)`, unique, not null |
| `provider` | `text` | not null, default `github` |
| `owner` | `text` | not null |
| `repo_name` | `text` | not null |
| `html_url` | `text` | not null |
| `default_branch` | `text` | not null, default `main` |
| `created_at` | `timestamptz` | not null |

#### `audit_events`

| Column | Type | Constraints |
| --- | --- | --- |
| `id` | `uuid` | primary key |
| `profile_id` | `uuid` | references `profiles(id)`, nullable |
| `project_id` | `uuid` | references `projects(id)`, nullable |
| `event_type` | `text` | not null |
| `payload` | `jsonb` | not null, default `{}` |
| `created_at` | `timestamptz` | not null |

### 5.2 Indexes

Planned indexes:

- `profiles(telegram_user_id)`.
- `telegram_chats(telegram_chat_id)`.
- `projects(owner_profile_id, updated_at desc)`.
- `project_members(profile_id, project_id)`.
- `project_stages(project_id, stage, status)`.
- `memory_items(profile_id, memory_type, updated_at desc)`.
- `memory_items(project_id, memory_type, updated_at desc)`.
- `conversation_messages(project_id, created_at desc)`.
- `generation_runs(project_id, created_at desc)`.
- `artifacts(project_id, artifact_type, created_at desc)`.

### 5.3 RLS Policy Design

All tables in exposed schemas must have RLS enabled.

MVP backend uses service role server-side. If a future public client accesses Supabase directly, policies must enforce:

- profiles are visible only to their owner;
- projects are visible only to `project_members`;
- project artifacts are visible only to project members;
- template metadata can be publicly readable if active;
- audit events are server-only.

Do not use user-editable metadata for authorization decisions.

## 6. Environment Variables

### 6.1 Required Runtime Variables

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | `local`, `staging` or `production` |
| `APP_BASE_URL` | public base URL for FastAPI/webhook callbacks |
| `APP_SECRET_KEY` | server-side signing/encryption secret |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token |
| `TELEGRAM_WEBHOOK_SECRET` | secret webhook path or header token |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | server-only Supabase service role key |
| `SUPABASE_STORAGE_BUCKET` | bucket for generated artifacts and ZIP files |
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_MODEL` | default generation model configured by operator |
| `GITHUB_TOKEN` | GitHub App installation token or PAT for local prototype |
| `GITHUB_OWNER` | GitHub org/user where MVP repos are created |
| `GITHUB_DEFAULT_PRIVATE` | `true` or `false` for repo visibility |
| `PROJECT_WORKDIR` | local temp directory for generated project assembly |
| `ZIP_MAX_BYTES` | max ZIP size before GitHub-only export |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING` or `ERROR` |

### 6.2 Optional Runtime Variables

| Variable | Purpose |
| --- | --- |
| `SENTRY_DSN` | error reporting |
| `OPENAI_TIMEOUT_SECONDS` | provider timeout override |
| `GITHUB_API_BASE_URL` | GitHub Enterprise compatibility |
| `RATE_LIMIT_PROJECTS_PER_USER_DAY` | simple MVP quota |
| `RATE_LIMIT_LLM_CALLS_PER_PROJECT` | generation budget guard |

## 7. API Contracts

FastAPI is not the primary user interface, but v1.0 needs HTTP boundaries for webhook delivery and internal inspection.

### 7.1 Health

`GET /health`

Response:

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

### 7.2 Telegram Webhook

`POST /webhooks/telegram/{secret}`

Request:

- raw Telegram update JSON.

Response:

```json
{
  "ok": true
}
```

Rules:

- reject invalid `secret`;
- persist inbound message before business processing;
- deduplicate Telegram `update_id`;
- enqueue or execute short MVP flow;
- never expose stack traces to Telegram.

### 7.3 Create Project

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
  "project_id": "uuid",
  "status": "clarifying",
  "next_message": "I can build this. Who will use the CRM: owner, staff, or both?"
}
```

### 7.4 Generate Project

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
  "project_id": "uuid",
  "status": "completed",
  "template": "crm",
  "github_url": "https://github.com/example/vuls-coffee-crm",
  "zip_artifact_id": null
}
```

### 7.5 Project Status

`GET /internal/projects/{project_id}`

Response:

```json
{
  "project_id": "uuid",
  "title": "Coffee CRM",
  "status": "completed",
  "selected_template_key": "crm",
  "repository_url": "https://github.com/example/vuls-coffee-crm",
  "updated_at": "2026-06-01T18:00:00Z"
}
```

### 7.6 Error Shape

All HTTP errors use:

```json
{
  "error": {
    "code": "project_not_found",
    "message": "Project was not found",
    "request_id": "uuid"
  }
}
```

## 8. Telegram Bot Flow

### 8.1 Commands

| Command | Behavior |
| --- | --- |
| `/start` | create/load profile, show welcome, language hint, main actions |
| `/new` | start new project intake |
| `/projects` | list recent projects |
| `/status` | show active project state |
| `/cancel` | cancel current intake/generation |
| `/help` | explain v1.0 capabilities and limits |

### 8.2 New Project Flow

```text
User: /new Create a CRM for a small coffee shop
Vuls:
  1. creates/loads profile
  2. saves inbound message
  3. creates project in clarifying status
  4. reads memory
  5. asks up to three clarifying questions if needed
  6. selects template
  7. asks user to choose ZIP or GitHub Repo
  8. generates project
  9. exports result
  10. sends final link/file
```

### 8.3 Callback Buttons

Required inline actions:

- `Generate ZIP`
- `Create GitHub Repo`
- `Cancel`
- `Show status`
- `Use CRM Template`
- `Use SaaS Template`
- `Use Marketplace Template`
- `Use AI Agent Template`
- `Use Dashboard Template`

### 8.4 User-Facing States

| State | Telegram message style |
| --- | --- |
| `clarifying` | one question, concise choices |
| `template_selection` | show recommended template and alternatives |
| `generating` | status update, no long logs |
| `exporting` | explain ZIP/GitHub export progress |
| `completed` | send GitHub URL or ZIP plus summary |
| `failed` | short apology, failure code, retry option |

## 9. Milestones

### Milestone 1: Project Skeleton and Tooling

**Goal:** Establish a Python 3.13 FastAPI/aiogram repository skeleton with testing and configuration conventions.

**Files to create:**

- `pyproject.toml`
- `.env.example`
- `.gitignore`
- `README.md`
- `Dockerfile`
- `docker-compose.yml`
- `src/vuls/__init__.py`
- `src/vuls/main.py`
- `src/vuls/core/config.py`
- `src/vuls/core/errors.py`
- `src/vuls/core/logging.py`
- `tests/unit/test_config.py`

**Dependencies:**

- Python 3.13
- FastAPI
- uvicorn
- aiogram
- pydantic
- pydantic-settings
- pytest
- ruff
- mypy

**Implementation tasks:**

- [ ] Initialize Python package metadata and dependency groups.
- [ ] Define settings model with required environment variables.
- [ ] Add app entrypoint that wires the FastAPI app factory without business integrations.
- [ ] Add lint, typecheck and test commands.
- [ ] Add `.env.example` with all required keys and safe example values.
- [ ] Add unit tests for settings validation.
- [ ] Commit as `chore: initialize Vuls Python service skeleton`.

**Acceptance criteria:**

- `python --version` reports Python 3.13 in the active environment.
- `pytest` runs and passes settings tests.
- `ruff check .` passes.
- `mypy src` passes or has a documented strict baseline.
- No production Telegram/OpenAI/GitHub calls exist yet.

### Milestone 2: FastAPI App and HTTP Contracts

**Goal:** Implement FastAPI boundaries for health, Telegram webhook ingress and internal project contracts.

**Files to create:**

- `src/vuls/api/app.py`
- `src/vuls/api/dependencies.py`
- `src/vuls/api/routes/health.py`
- `src/vuls/api/routes/telegram.py`
- `src/vuls/api/routes/projects.py`
- `src/vuls/api/routes/internal.py`
- `docs/api/v1-contracts.md`
- `tests/unit/api/test_health.py`
- `tests/unit/api/test_telegram_webhook.py`
- `tests/unit/api/test_project_contracts.py`

**Dependencies:**

- Milestone 1
- FastAPI test client
- Pydantic request/response models

**Implementation tasks:**

- [ ] Write tests for `GET /health`.
- [ ] Implement FastAPI app factory and health route.
- [ ] Write tests for invalid Telegram webhook secret.
- [ ] Implement Telegram webhook route with secret validation.
- [ ] Write request/response tests for internal project contracts.
- [ ] Implement typed contract shells that delegate to services.
- [ ] Document contracts in `docs/api/v1-contracts.md`.
- [ ] Commit as `feat: add FastAPI v1 contract boundaries`.

**Acceptance criteria:**

- `GET /health` returns `status=ok`.
- Telegram webhook rejects invalid secret.
- Project contract schemas validate documented request/response shapes.
- Routes do not directly call OpenAI, Supabase or GitHub clients.

### Milestone 3: Supabase Schema and Repository Layer

**Goal:** Create the v1.0 database schema and repository interfaces for users, projects, memory, templates, artifacts and audit events.

**Files to create:**

- `supabase/config.toml`
- Supabase CLI-generated migration file for `init_vuls_v1`
- `src/vuls/db/client.py`
- `src/vuls/db/models.py`
- `src/vuls/db/repositories/users.py`
- `src/vuls/db/repositories/projects.py`
- `src/vuls/db/repositories/memory.py`
- `src/vuls/db/repositories/templates.py`
- `src/vuls/db/repositories/artifacts.py`
- `src/vuls/db/repositories/audit.py`
- `tests/unit/db/test_project_repository.py`
- `tests/unit/db/test_memory_repository.py`
- `tests/unit/db/test_template_repository.py`

**Dependencies:**

- Milestone 1
- Supabase CLI
- Supabase Python client
- Postgres UUID support through `pgcrypto`

**Implementation tasks:**

- [ ] Run `supabase --help` and `supabase migration new init_vuls_v1` during implementation.
- [ ] Create tables from Section 5.
- [ ] Enable RLS on all exposed tables.
- [ ] Add indexes from Section 5.2.
- [ ] Add repository methods for create/load profile.
- [ ] Add repository methods for create/update/list projects.
- [ ] Add repository methods for read/write memory items.
- [ ] Add repository methods for template catalog reads.
- [ ] Add repository methods for artifacts and audit events.
- [ ] Add unit tests with mocked Supabase client calls.
- [ ] Commit as `feat: add Supabase persistence layer`.

**Acceptance criteria:**

- Migration creates all v1.0 tables and indexes.
- RLS is enabled on all public tables.
- No code exposes `SUPABASE_SERVICE_ROLE_KEY` outside server settings.
- Repository tests cover success and not-found paths.
- Supabase migration filename is generated by CLI, not manually invented during implementation.

### Milestone 4: Memory Layer

**Goal:** Persist and retrieve user, project, conversation and knowledge memory for Telegram continuation.

**Files to create:**

- `src/vuls/memory/schemas.py`
- `src/vuls/memory/service.py`
- `src/vuls/memory/summarizer.py`
- `tests/unit/memory/test_memory_service.py`
- `tests/unit/memory/test_conversation_summary.py`

**Dependencies:**

- Milestone 3
- Pydantic models
- Repository interfaces

**Implementation tasks:**

- [ ] Define typed memory schemas for `user`, `project`, `conversation`, `knowledge`.
- [ ] Implement context assembly for a project generation request.
- [ ] Implement durable fact write behavior after intake and generation.
- [ ] Implement conversation summary creation with deterministic local fallback.
- [ ] Add tests for loading existing project context.
- [ ] Add tests for writing conversation memory.
- [ ] Commit as `feat: add project memory layer`.

**Acceptance criteria:**

- Returning user can continue an existing project by project id.
- Memory service returns bounded context for LLM prompts.
- Raw conversation messages and durable memory facts are separate.
- Memory writes include source, confidence, profile id and project id when available.

### Milestone 5: Template System

**Goal:** Add template registry and five v1.0 templates: CRM, SaaS, Marketplace, AI Agent and Dashboard.

**Files to create:**

- `src/vuls/templates/schemas.py`
- `src/vuls/templates/registry.py`
- `src/vuls/templates/renderer.py`
- `src/vuls/templates/catalog/crm/template.yaml`
- `src/vuls/templates/catalog/crm/prompts.md`
- `src/vuls/templates/catalog/crm/files.yaml`
- `src/vuls/templates/catalog/saas/template.yaml`
- `src/vuls/templates/catalog/saas/prompts.md`
- `src/vuls/templates/catalog/saas/files.yaml`
- `src/vuls/templates/catalog/marketplace/template.yaml`
- `src/vuls/templates/catalog/marketplace/prompts.md`
- `src/vuls/templates/catalog/marketplace/files.yaml`
- `src/vuls/templates/catalog/ai_agent/template.yaml`
- `src/vuls/templates/catalog/ai_agent/prompts.md`
- `src/vuls/templates/catalog/ai_agent/files.yaml`
- `src/vuls/templates/catalog/dashboard/template.yaml`
- `src/vuls/templates/catalog/dashboard/prompts.md`
- `src/vuls/templates/catalog/dashboard/files.yaml`
- `tests/unit/templates/test_registry.py`
- `tests/unit/templates/test_template_selection.py`

**Dependencies:**

- Milestone 3
- YAML parser
- Memory service for preferred stack and project context

**Implementation tasks:**

- [ ] Define template manifest schema.
- [ ] Implement registry loading from `src/vuls/templates/catalog`.
- [ ] Implement deterministic keyword-based template preselection.
- [ ] Add LLM-ready template rendering context.
- [ ] Add all five template manifests.
- [ ] Add tests for catalog loading.
- [ ] Add tests for template selection confidence behavior.
- [ ] Commit as `feat: add v1 template catalog`.

**Acceptance criteria:**

- All five templates load successfully.
- Template selection can choose CRM for coffee-shop CRM input.
- Low-confidence selection returns a clarification question instead of guessing.
- Template definitions include i18n key expectations and README rules.

### Milestone 6: OpenAI / LLM Gateway

**Goal:** Add OpenAI-backed generation gateway with structured outputs, prompt rendering and usage logging.

**Files to create:**

- `src/vuls/llm/schemas.py`
- `src/vuls/llm/prompts.py`
- `src/vuls/llm/safety.py`
- `src/vuls/llm/openai_client.py`
- `src/vuls/llm/gateway.py`
- `tests/unit/llm/test_prompt_rendering.py`
- `tests/unit/llm/test_structured_generation.py`
- `tests/unit/llm/test_safety.py`

**Dependencies:**

- Milestone 4
- Milestone 5
- OpenAI Python SDK
- Pydantic output schemas

**Implementation tasks:**

- [ ] Define `ProjectBrief`, `ClarificationQuestion`, `TemplateSelection` and `GeneratedProjectManifest` schemas.
- [ ] Add prompt rendering for brief normalization.
- [ ] Add prompt rendering for template-based project manifest generation.
- [ ] Implement OpenAI adapter behind gateway interface.
- [ ] Validate structured model output before persistence.
- [ ] Record provider, model and usage metadata.
- [ ] Add safety checks for disallowed project requests.
- [ ] Add unit tests with mocked OpenAI responses.
- [ ] Commit as `feat: add OpenAI generation gateway`.

**Acceptance criteria:**

- LLM gateway can be tested without real network calls.
- Invalid JSON/model output fails with a typed error.
- Generated manifest includes file paths, file contents, README summary and env var list.
- Usage metadata is available for `generation_runs`.

### Milestone 7: Project Generation and ZIP Export

**Goal:** Generate a project file manifest from template plus LLM output and export it as a ZIP artifact.

**Files to create:**

- `src/vuls/generation/file_manifest.py`
- `src/vuls/generation/project_builder.py`
- `src/vuls/generation/zip_exporter.py`
- `src/vuls/generation/orchestrator.py`
- `tests/unit/generation/test_file_manifest.py`
- `tests/unit/generation/test_zip_exporter.py`
- `tests/integration/test_project_generation_flow.py`

**Dependencies:**

- Milestone 3
- Milestone 4
- Milestone 5
- Milestone 6
- local temporary filesystem access under `PROJECT_WORKDIR`

**Implementation tasks:**

- [ ] Define safe file manifest rules.
- [ ] Reject absolute paths and path traversal.
- [ ] Assemble project files in temporary workspace.
- [ ] Generate README and `.env.example` from manifest.
- [ ] Create ZIP artifact.
- [ ] Store artifact metadata in Supabase.
- [ ] Add integration test from idea to ZIP artifact metadata.
- [ ] Commit as `feat: add project generation and ZIP export`.

**Acceptance criteria:**

- Project generation never writes outside `PROJECT_WORKDIR`.
- ZIP export includes generated source files and README.
- ZIP size is checked against `ZIP_MAX_BYTES`.
- Artifact record is written with project id and generation run id.

### Milestone 8: GitHub API Export

**Goal:** Create GitHub repositories and commit generated project files through the GitHub API.

**Files to create:**

- `src/vuls/github/schemas.py`
- `src/vuls/github/client.py`
- `src/vuls/github/service.py`
- `tests/unit/github/test_github_service.py`
- `tests/integration/test_github_export_flow.py`

**Dependencies:**

- Milestone 7
- GitHub API token or GitHub App installation token
- Repository manifest from generation flow

**Implementation tasks:**

- [ ] Define GitHub export request/response schemas.
- [ ] Implement repository name normalization.
- [ ] Implement repo creation call through GitHub API.
- [ ] Implement initial file commit.
- [ ] Handle repo name conflict with deterministic suffix.
- [ ] Persist repository metadata.
- [ ] Add mocked GitHub API unit tests.
- [ ] Add integration test using fake GitHub client.
- [ ] Commit as `feat: add GitHub repository export`.

**Acceptance criteria:**

- Service can export a generated manifest to a GitHub repository.
- Name conflicts return a retryable internal result.
- Secrets are never included in committed files.
- Repository URL is persisted and returned to caller.

### Milestone 9: Telegram Bot Flow

**Goal:** Connect aiogram handlers to the v1.0 project generation flow.

**Files to create:**

- `src/vuls/bot/app.py`
- `src/vuls/bot/dispatcher.py`
- `src/vuls/bot/keyboards.py`
- `src/vuls/bot/messages.py`
- `src/vuls/bot/handlers/start.py`
- `src/vuls/bot/handlers/new_project.py`
- `src/vuls/bot/handlers/projects.py`
- `src/vuls/bot/handlers/status.py`
- `src/vuls/bot/handlers/callbacks.py`
- `tests/unit/bot/test_start_handler.py`
- `tests/unit/bot/test_new_project_handler.py`
- `tests/unit/bot/test_status_handler.py`
- `tests/integration/test_telegram_intake_flow.py`

**Dependencies:**

- Milestone 2
- Milestone 7
- Milestone 8
- aiogram
- i18n locale files

**Implementation tasks:**

- [ ] Implement `/start` profile creation/loading flow.
- [ ] Implement `/new` idea intake.
- [ ] Implement clarification state handling.
- [ ] Implement ZIP/GitHub export choice callbacks.
- [ ] Implement `/projects` list.
- [ ] Implement `/status` active project summary.
- [ ] Implement failure messages with retry/cancel options.
- [ ] Add handler tests with fixture updates.
- [ ] Commit as `feat: connect Telegram bot MVP flow`.

**Acceptance criteria:**

- User can start a new project from Telegram text.
- Bot asks no more than three clarification questions.
- Bot offers ZIP or GitHub export.
- Bot returns final ZIP artifact or GitHub repo URL.
- Bot can show recent projects and active project status.

### Milestone 10: i18n System Messages

**Goal:** Add system translation files for the required 12 languages and prevent hardcoded user-facing bot text.

**Files to create:**

- `src/vuls/i18n/__init__.py`
- `src/vuls/i18n/locales/ru.json`
- `src/vuls/i18n/locales/en.json`
- `src/vuls/i18n/locales/es.json`
- `src/vuls/i18n/locales/de.json`
- `src/vuls/i18n/locales/fr.json`
- `src/vuls/i18n/locales/pt.json`
- `src/vuls/i18n/locales/it.json`
- `src/vuls/i18n/locales/tr.json`
- `src/vuls/i18n/locales/ar.json`
- `src/vuls/i18n/locales/zh.json`
- `src/vuls/i18n/locales/ja.json`
- `src/vuls/i18n/locales/ko.json`
- `tests/unit/test_i18n.py`

**Dependencies:**

- Milestone 9
- Message key inventory from bot handlers

**Implementation tasks:**

- [ ] Define required message keys used by Telegram flow.
- [ ] Create locale JSON files for all 12 languages.
- [ ] Implement locale loading and fallback to English.
- [ ] Replace bot user-facing literals with message keys.
- [ ] Add tests for missing keys across locales.
- [ ] Add RTL metadata for Arabic.
- [ ] Commit as `feat: add multilingual bot messages`.

**Acceptance criteria:**

- All 12 locale files exist.
- Every locale has the same keys.
- Bot handlers use message keys instead of hardcoded user-facing strings.
- English fallback works for unknown language codes.

### Milestone 11: End-to-End MVP Flow

**Goal:** Validate the complete v1.0 path from Telegram-style input to ZIP/GitHub result.

**Files to create:**

- `tests/integration/test_vuls_v1_e2e_zip.py`
- `tests/integration/test_vuls_v1_e2e_github.py`
- `docs/operations/local-development.md`
- `docs/operations/release-checklist.md`

**Dependencies:**

- Milestones 1 through 10
- mocked OpenAI client for deterministic CI
- fake GitHub client for deterministic CI
- test Supabase project or mocked repository layer

**Implementation tasks:**

- [ ] Add E2E test for `/new` to ZIP export.
- [ ] Add E2E test for `/new` to GitHub export with fake GitHub client.
- [ ] Add failure-path test for LLM output validation error.
- [ ] Add local development guide.
- [ ] Add release checklist.
- [ ] Run full test suite, lint and typecheck.
- [ ] Commit as `test: verify Vuls v1 MVP flow`.

**Acceptance criteria:**

- E2E ZIP path passes.
- E2E GitHub path passes with fake GitHub API.
- Failure path returns user-safe Telegram error.
- Local development docs explain required env vars and startup commands.

## 10. Implementation Order

1. Milestone 1: Project Skeleton and Tooling.
2. Milestone 2: FastAPI App and HTTP Contracts.
3. Milestone 3: Supabase Schema and Repository Layer.
4. Milestone 4: Memory Layer.
5. Milestone 5: Template System.
6. Milestone 6: OpenAI / LLM Gateway.
7. Milestone 7: Project Generation and ZIP Export.
8. Milestone 8: GitHub API Export.
9. Milestone 9: Telegram Bot Flow.
10. Milestone 10: i18n System Messages.
11. Milestone 11: End-to-End MVP Flow.

Do not combine multiple major milestones in one implementation pass.

## 11. Approval Gate

After this plan is approved, implementation should start with Milestone 1 only. No production code should be written before approval.
