create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table public.profiles (
  id uuid primary key default gen_random_uuid(),
  telegram_user_id bigint not null unique,
  telegram_username text,
  display_name text,
  language_code text not null default 'en',
  preferred_stack jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.telegram_chats (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references public.profiles(id) on delete cascade,
  telegram_chat_id bigint not null unique,
  chat_type text not null,
  last_seen_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create table public.projects (
  id uuid primary key default gen_random_uuid(),
  owner_profile_id uuid not null references public.profiles(id) on delete cascade,
  title text not null,
  slug text not null,
  status text not null default 'draft'
    check (status in ('draft', 'clarifying', 'generating', 'exporting', 'completed', 'failed', 'cancelled')),
  selected_template_key text,
  brief jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.project_members (
  project_id uuid not null references public.projects(id) on delete cascade,
  profile_id uuid not null references public.profiles(id) on delete cascade,
  role text not null check (role in ('owner', 'editor', 'viewer')),
  created_at timestamptz not null default now(),
  primary key (project_id, profile_id)
);

create table public.project_stages (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  stage text not null
    check (stage in ('intake', 'clarification', 'template_selection', 'generation', 'export', 'completed')),
  status text not null default 'pending'
    check (status in ('pending', 'running', 'completed', 'failed', 'cancelled')),
  input jsonb not null default '{}'::jsonb,
  output jsonb not null default '{}'::jsonb,
  error jsonb,
  started_at timestamptz,
  completed_at timestamptz
);

create table public.memory_items (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references public.profiles(id) on delete cascade,
  project_id uuid references public.projects(id) on delete cascade,
  memory_type text not null check (memory_type in ('user', 'project', 'conversation', 'knowledge')),
  source text not null check (source in ('telegram', 'generation', 'system', 'manual')),
  content jsonb not null,
  summary text not null,
  confidence numeric(3, 2) not null default 1.00 check (confidence >= 0 and confidence <= 1),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.conversation_messages (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references public.profiles(id) on delete cascade,
  project_id uuid references public.projects(id) on delete cascade,
  telegram_message_id bigint,
  direction text not null check (direction in ('inbound', 'outbound')),
  message_type text not null check (message_type in ('text', 'command', 'callback', 'document', 'system')),
  text text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table public.templates (
  id uuid primary key default gen_random_uuid(),
  key text not null unique,
  name text not null,
  description text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table public.template_versions (
  id uuid primary key default gen_random_uuid(),
  template_id uuid not null references public.templates(id) on delete cascade,
  version text not null,
  manifest jsonb not null,
  created_at timestamptz not null default now(),
  unique (template_id, version)
);

create table public.generation_runs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  template_version_id uuid references public.template_versions(id) on delete set null,
  status text not null default 'queued'
    check (status in ('queued', 'running', 'completed', 'failed', 'cancelled')),
  provider text not null,
  model text not null,
  input_summary text not null,
  output_manifest jsonb,
  usage jsonb not null default '{}'::jsonb,
  error jsonb,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create table public.artifacts (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  generation_run_id uuid references public.generation_runs(id) on delete set null,
  artifact_type text not null check (artifact_type in ('manifest', 'zip', 'readme', 'source_snapshot', 'log')),
  storage_path text,
  content jsonb,
  created_at timestamptz not null default now()
);

create table public.repositories (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null unique references public.projects(id) on delete cascade,
  provider text not null default 'github',
  owner text not null,
  repo_name text not null,
  html_url text not null,
  default_branch text not null default 'main',
  created_at timestamptz not null default now()
);

create table public.audit_events (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references public.profiles(id) on delete set null,
  project_id uuid references public.projects(id) on delete cascade,
  event_type text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index profiles_telegram_user_id_idx on public.profiles (telegram_user_id);
create index telegram_chats_telegram_chat_id_idx on public.telegram_chats (telegram_chat_id);
create index projects_owner_updated_idx on public.projects (owner_profile_id, updated_at desc);
create index project_members_profile_project_idx on public.project_members (profile_id, project_id);
create index project_stages_project_stage_status_idx on public.project_stages (project_id, stage, status);
create index memory_items_profile_type_updated_idx on public.memory_items (profile_id, memory_type, updated_at desc);
create index memory_items_project_type_updated_idx on public.memory_items (project_id, memory_type, updated_at desc);
create index conversation_messages_project_created_idx on public.conversation_messages (project_id, created_at desc);
create index generation_runs_project_created_idx on public.generation_runs (project_id, created_at desc);
create index artifacts_project_type_created_idx on public.artifacts (project_id, artifact_type, created_at desc);

create trigger profiles_set_updated_at
before update on public.profiles
for each row execute function public.set_updated_at();

create trigger projects_set_updated_at
before update on public.projects
for each row execute function public.set_updated_at();

create trigger memory_items_set_updated_at
before update on public.memory_items
for each row execute function public.set_updated_at();

alter table public.profiles enable row level security;
alter table public.telegram_chats enable row level security;
alter table public.projects enable row level security;
alter table public.project_members enable row level security;
alter table public.project_stages enable row level security;
alter table public.memory_items enable row level security;
alter table public.conversation_messages enable row level security;
alter table public.templates enable row level security;
alter table public.template_versions enable row level security;
alter table public.generation_runs enable row level security;
alter table public.artifacts enable row level security;
alter table public.repositories enable row level security;
alter table public.audit_events enable row level security;
