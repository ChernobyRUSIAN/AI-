import json
import re
from collections.abc import Mapping
from dataclasses import dataclass

from vuls.llm.schemas import GeneratedProjectFile, GeneratedProjectManifest, ProjectBrief

CRM_TEMPLATE_KEY = "crm"
CRM_NEXT_MVP_STACK = ("Next.js", "TypeScript", "Tailwind CSS")
REACT_HOOK_PATTERN = re.compile(
    r"\b(useState|useEffect|useMemo|useCallback|useReducer|useRef|"
    r"useRouter|useSearchParams|usePathname)\s*\("
)


@dataclass(frozen=True)
class CRMDomainProfile:
    key: str
    keywords: tuple[str, ...]
    dashboard_title: str
    dashboard_description: str
    customer_singular: str
    customer_plural: str
    team_singular: str
    team_plural: str
    order_singular: str
    order_plural: str
    service_singular: str
    service_plural: str
    task_singular: str
    task_plural: str
    customer_page_title: str
    order_page_title: str
    task_page_title: str
    task_page_description: str
    sample_customer_name: str
    sample_customer_email: str
    sample_customer_phone: str
    sample_order_service: str
    sample_order_price: str
    sample_task_title: str
    sample_task_owner: str


DOMAIN_NEUTRAL_PROFILE = CRMDomainProfile(
    key="generic",
    keywords=(),
    dashboard_title="CRM operations",
    dashboard_description="Track customers, orders and tasks from one practical CRM workspace.",
    customer_singular="Customer",
    customer_plural="Customers",
    team_singular="Team member",
    team_plural="Team",
    order_singular="Order",
    order_plural="Orders",
    service_singular="Service",
    service_plural="Services",
    task_singular="Task",
    task_plural="Tasks",
    customer_page_title="Customer list",
    order_page_title="Customer orders",
    task_page_title="Team task board",
    task_page_description=(
        "Coordinate team follow-ups, customer communication and operational work."
    ),
    sample_customer_name="Alex Morgan",
    sample_customer_email="alex@example.com",
    sample_customer_phone="+1 555 0100",
    sample_order_service="Standard service",
    sample_order_price="85",
    sample_task_title="Follow up with key customer",
    sample_task_owner="Operations",
)


CRM_DOMAIN_PROFILES = (
    CRMDomainProfile(
        key="dentistry",
        keywords=("dentistry", "dental", "dentist", "clinic"),
        dashboard_title="Dental clinic operations",
        dashboard_description=(
            "Track patients, appointments, treatments and clinic work in one CRM workspace."
        ),
        customer_singular="Patient",
        customer_plural="Patients",
        team_singular="Doctor",
        team_plural="Doctors",
        order_singular="Appointment",
        order_plural="Appointments",
        service_singular="Treatment",
        service_plural="Treatments",
        task_singular="Treatment",
        task_plural="Treatments",
        customer_page_title="Patient list",
        order_page_title="Appointments",
        task_page_title="Treatment board",
        task_page_description="Coordinate treatment plans, patient follow-ups and doctor handoffs.",
        sample_customer_name="Mia Johnson",
        sample_customer_email="mia.patient@example.com",
        sample_customer_phone="+1 555 0111",
        sample_order_service="Dental cleaning",
        sample_order_price="120",
        sample_task_title="Prepare treatment plan",
        sample_task_owner="Dr. Carter",
    ),
    CRMDomainProfile(
        key="fitness",
        keywords=("fitness", "gym", "trainer", "workout", "membership"),
        dashboard_title="Fitness club operations",
        dashboard_description=(
            "Track members, trainers, classes and memberships from one CRM workspace."
        ),
        customer_singular="Member",
        customer_plural="Members",
        team_singular="Trainer",
        team_plural="Trainers",
        order_singular="Class",
        order_plural="Classes",
        service_singular="Membership",
        service_plural="Memberships",
        task_singular="Membership",
        task_plural="Memberships",
        customer_page_title="Member list",
        order_page_title="Classes",
        task_page_title="Membership board",
        task_page_description="Coordinate trainer follow-ups, renewals and member success work.",
        sample_customer_name="Jordan Lee",
        sample_customer_email="jordan.member@example.com",
        sample_customer_phone="+1 555 0122",
        sample_order_service="Strength class",
        sample_order_price="45",
        sample_task_title="Renew membership",
        sample_task_owner="Lead trainer",
    ),
    CRMDomainProfile(
        key="beauty_salon",
        keywords=("beauty", "salon", "spa", "master", "booking"),
        dashboard_title="Beauty salon operations",
        dashboard_description=(
            "Track clients, masters, services and bookings from one CRM workspace."
        ),
        customer_singular="Client",
        customer_plural="Clients",
        team_singular="Master",
        team_plural="Masters",
        order_singular="Booking",
        order_plural="Bookings",
        service_singular="Service",
        service_plural="Services",
        task_singular="Service",
        task_plural="Services",
        customer_page_title="Client list",
        order_page_title="Bookings",
        task_page_title="Service board",
        task_page_description=(
            "Coordinate master schedules, client follow-ups and service preparation."
        ),
        sample_customer_name="Sofia Martinez",
        sample_customer_email="sofia.client@example.com",
        sample_customer_phone="+1 555 0133",
        sample_order_service="Hair styling",
        sample_order_price="70",
        sample_task_title="Confirm booking details",
        sample_task_owner="Senior master",
    ),
    CRMDomainProfile(
        key="auto_service",
        keywords=(
            "auto service",
            "autoservice",
            "car service",
            "repair shop",
            "mechanic",
        ),
        dashboard_title="Auto service operations",
        dashboard_description=(
            "Track vehicles, mechanics, repairs and work orders from one CRM workspace."
        ),
        customer_singular="Vehicle",
        customer_plural="Vehicles",
        team_singular="Mechanic",
        team_plural="Mechanics",
        order_singular="Work Order",
        order_plural="Work Orders",
        service_singular="Repair",
        service_plural="Repairs",
        task_singular="Repair",
        task_plural="Repairs",
        customer_page_title="Vehicle list",
        order_page_title="Work Orders",
        task_page_title="Repair board",
        task_page_description=(
            "Coordinate mechanic assignments, repair follow-ups and work order progress."
        ),
        sample_customer_name="Toyota Camry",
        sample_customer_email="owner@example.com",
        sample_customer_phone="+1 555 0144",
        sample_order_service="Brake repair",
        sample_order_price="240",
        sample_task_title="Inspect repair quality",
        sample_task_owner="Lead mechanic",
    ),
)


def ensure_crm_next_mvp_manifest(
    *,
    manifest: GeneratedProjectManifest,
    template_key: str,
    brief: ProjectBrief,
) -> GeneratedProjectManifest:
    if template_key != CRM_TEMPLATE_KEY:
        return manifest

    scaffold_files = _crm_next_mvp_files(brief=brief)
    files_by_path = {file.path: file for file in manifest.files}

    for scaffold_file in scaffold_files:
        existing_file = files_by_path.get(scaffold_file.path)
        if existing_file is None or _should_replace_with_scaffold(
            path=scaffold_file.path,
            content=existing_file.content,
        ):
            files_by_path[scaffold_file.path] = scaffold_file

    files_by_path = {
        path: _sanitize_app_router_file(file)
        for path, file in files_by_path.items()
    }

    ordered_files = _ordered_files(
        original_files=manifest.files,
        scaffold_files=scaffold_files,
        files_by_path=files_by_path,
    )
    return manifest.model_copy(
        update={
            "tech_stack": _merge_tech_stack(manifest.tech_stack),
            "files": ordered_files,
        }
    )


def _crm_next_mvp_files(*, brief: ProjectBrief) -> list[GeneratedProjectFile]:
    app_name = brief.title.strip() or "CRM Workspace"
    domain_profile = _detect_crm_domain(brief)
    return [
        GeneratedProjectFile(
            path="package.json",
            content=_package_json(app_name),
            purpose="Next.js App Router package manifest with TypeScript and Tailwind.",
        ),
        GeneratedProjectFile(
            path="tsconfig.json",
            content=_tsconfig_json(),
            purpose="TypeScript compiler settings for the Next.js app.",
        ),
        GeneratedProjectFile(
            path="next.config.ts",
            content=_next_config_ts(),
            purpose="Next.js configuration.",
        ),
        GeneratedProjectFile(
            path="postcss.config.js",
            content=_postcss_config_js(),
            purpose="PostCSS configuration for Tailwind.",
        ),
        GeneratedProjectFile(
            path="tailwind.config.ts",
            content=_tailwind_config_ts(),
            purpose="Tailwind configuration for App Router source files.",
        ),
        GeneratedProjectFile(
            path="schema.sql",
            content=_schema_sql(),
            purpose="Supabase schema for CRM customers, orders and tasks.",
        ),
        GeneratedProjectFile(
            path="sample-data.sql",
            content=_sample_data_sql(domain_profile),
            purpose="Optional Supabase seed data tailored to the detected CRM domain.",
        ),
        GeneratedProjectFile(
            path="env.example",
            content=_env_example(),
            purpose="Example Supabase environment variables for local setup.",
        ),
        GeneratedProjectFile(
            path="src/app/layout.tsx",
            content=_layout_tsx(app_name, domain_profile),
            purpose="Root App Router layout with CRM navigation.",
        ),
        GeneratedProjectFile(
            path="src/app/globals.css",
            content=_globals_css(),
            purpose="Tailwind base styles and SaaS CRM theme tokens.",
        ),
        GeneratedProjectFile(
            path="src/app/page.tsx",
            content=_root_page_tsx(),
            purpose="Root route redirect to the CRM dashboard.",
        ),
        GeneratedProjectFile(
            path="src/lib/database.types.ts",
            content=_database_types_ts(),
            purpose="Supabase database types for CRM tables.",
        ),
        GeneratedProjectFile(
            path="src/lib/supabase.ts",
            content=_supabase_ts(),
            purpose="Lazy Supabase client factory for runtime database access.",
        ),
        GeneratedProjectFile(
            path="src/app/dashboard/page.tsx",
            content=_dashboard_page_tsx(domain_profile),
            purpose="Dashboard with metric cards for customers, orders and tasks.",
        ),
        GeneratedProjectFile(
            path="src/app/customers/actions.ts",
            content=_customers_actions_ts(),
            purpose="Supabase-backed customer CRUD server actions.",
        ),
        GeneratedProjectFile(
            path="src/app/customers/page.tsx",
            content=_customers_page_tsx(domain_profile),
            purpose="Supabase-backed customer list and CRUD forms.",
        ),
        GeneratedProjectFile(
            path="src/app/orders/actions.ts",
            content=_orders_actions_ts(),
            purpose="Supabase-backed order CRUD server actions.",
        ),
        GeneratedProjectFile(
            path="src/app/orders/page.tsx",
            content=_orders_page_tsx(domain_profile),
            purpose="Supabase-backed order list with status tracking.",
        ),
        GeneratedProjectFile(
            path="src/app/tasks/actions.ts",
            content=_tasks_actions_ts(),
            purpose="Supabase-backed task retrieval for the dashboard and task board.",
        ),
        GeneratedProjectFile(
            path="src/app/tasks/page.tsx",
            content=_tasks_page_tsx(domain_profile),
            purpose="Task board for staff follow-ups and operational work.",
        ),
    ]


def _detect_crm_domain(brief: ProjectBrief) -> CRMDomainProfile:
    haystack = " ".join(
        [
            brief.title,
            brief.goal,
            " ".join(brief.target_users),
            " ".join(brief.must_have_features),
        ]
    ).casefold()
    for profile in CRM_DOMAIN_PROFILES:
        if any(keyword.casefold() in haystack for keyword in profile.keywords):
            return profile
    return DOMAIN_NEUTRAL_PROFILE


def _should_replace_with_scaffold(*, path: str, content: str) -> bool:
    normalized_content = content.casefold()
    if _is_app_router_file(path) and _uses_pages_router(content):
        return True
    if _is_app_router_file(path) and _uses_react_hooks(content) and not _is_client_component(
        content
    ):
        return True
    if path == "package.json":
        return _should_replace_package_manifest(content)
    if path == "tsconfig.json":
        return _should_replace_tsconfig(content)
    if len(content.strip()) < 240:
        return True
    if any(marker in normalized_content for marker in ("placeholder", "todo", "coming soon")):
        return True

    required_tokens_by_path = {
        "schema.sql": ("public.customers", "public.orders", "public.tasks"),
        "sample-data.sql": ("public.customers", "public.orders", "public.tasks"),
        "env.example": ("next_public_supabase_url", "next_public_supabase_anon_key"),
        "src/lib/database.types.ts": ("customers", "orders", "tasks"),
        "src/lib/supabase.ts": ("createclient", "getsupabaseclient"),
        "src/app/layout.tsx": ("globals.css", "dashboard", "customers", "orders", "tasks"),
        "src/app/page.tsx": ("next/navigation", "redirect"),
        "src/app/dashboard/page.tsx": ("listcustomers", "listorders", "total customers"),
        "src/app/customers/actions.ts": (
            "getsupabaseclient",
            "createcustomer",
            "updatecustomer",
            "deletecustomer",
        ),
        "src/app/customers/page.tsx": ("listcustomers", "<form", "createcustomer"),
        "src/app/orders/actions.ts": (
            "getsupabaseclient",
            "createorder",
            "updateorderstatus",
            "deleteorder",
        ),
        "src/app/orders/page.tsx": ("listorders", "createorder", "order.status"),
        "src/app/tasks/actions.ts": ("getsupabaseclient", "listtasks"),
        "src/app/tasks/page.tsx": ("listtasks", "task.status"),
    }
    required_tokens = required_tokens_by_path.get(path)
    if required_tokens is None:
        return False
    return not all(token in normalized_content for token in required_tokens)


def _should_replace_package_manifest(content: str) -> bool:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return True

    if not isinstance(payload, dict):
        return True

    scripts = payload.get("scripts")
    dependencies = payload.get("dependencies")
    dev_dependencies = payload.get("devDependencies")

    if not isinstance(scripts, dict):
        return True
    if not isinstance(dependencies, dict):
        return True
    if not isinstance(dev_dependencies, dict):
        return True
    if scripts.get("build") != "next build":
        return True

    dependency_requirements = {
        "@supabase/supabase-js": ("^2.", "~2.", "2."),
        "next": ("^15.", "~15.", "15."),
        "react": ("^19.", "~19.", "19."),
        "react-dom": ("^19.", "~19.", "19."),
    }
    dev_dependency_requirements = {
        "@types/node": ("^22.", "~22.", "22."),
        "@types/react": ("^19.", "~19.", "19."),
        "@types/react-dom": ("^19.", "~19.", "19."),
        "autoprefixer": ("^10.", "~10.", "10."),
        "postcss": ("^8.", "~8.", "8."),
        "tailwindcss": ("^3.", "~3.", "3."),
        "typescript": ("^5.", "~5.", "5."),
    }

    return _missing_required_versions(
        dependencies=dependencies,
        requirements=dependency_requirements,
    ) or _missing_required_versions(
        dependencies=dev_dependencies,
        requirements=dev_dependency_requirements,
    )


def _missing_required_versions(
    *,
    dependencies: Mapping[object, object],
    requirements: Mapping[str, tuple[str, ...]],
) -> bool:
    for package_name, allowed_prefixes in requirements.items():
        version = dependencies.get(package_name)
        if not isinstance(version, str):
            return True
        normalized_version = version.strip()
        if not normalized_version.startswith(allowed_prefixes):
            return True
    return False


def _should_replace_tsconfig(content: str) -> bool:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return True

    if not isinstance(payload, dict):
        return True

    compiler_options = payload.get("compilerOptions")
    if not isinstance(compiler_options, dict):
        return True

    paths = compiler_options.get("paths")
    if not isinstance(paths, dict):
        return True

    app_alias = paths.get("@/*")
    if app_alias != ["./src/*"]:
        return True

    include = payload.get("include")
    if not isinstance(include, list) or ".next/types/**/*.ts" not in include:
        return True

    return compiler_options.get("moduleResolution") != "bundler"


def _sanitize_app_router_file(file: GeneratedProjectFile) -> GeneratedProjectFile:
    if not _is_app_router_file(file.path):
        return file

    content = file.content
    if _uses_pages_router(content):
        content = content.replace('"next/router"', '"next/navigation"')
        content = content.replace("'next/router'", '"next/navigation"')
    if _uses_react_hooks(content) and not _is_client_component(content):
        content = f'"use client";\n\n{content}'

    if content == file.content:
        return file
    return file.model_copy(update={"content": content})


def _is_app_router_file(path: str) -> bool:
    normalized_path = path.replace("\\", "/")
    return normalized_path.startswith("src/app/") and normalized_path.endswith((".tsx", ".ts"))


def _uses_pages_router(content: str) -> bool:
    return "next/router" in content


def _uses_react_hooks(content: str) -> bool:
    return REACT_HOOK_PATTERN.search(content) is not None


def _is_client_component(content: str) -> bool:
    stripped = content.lstrip()
    return stripped.startswith('"use client"') or stripped.startswith("'use client'")


def _ordered_files(
    *,
    original_files: list[GeneratedProjectFile],
    scaffold_files: list[GeneratedProjectFile],
    files_by_path: dict[str, GeneratedProjectFile],
) -> list[GeneratedProjectFile]:
    ordered: list[GeneratedProjectFile] = []
    seen_paths: set[str] = set()

    for generated_file in original_files:
        if generated_file.path in seen_paths:
            continue
        ordered.append(files_by_path[generated_file.path])
        seen_paths.add(generated_file.path)

    for scaffold_file in scaffold_files:
        if scaffold_file.path in seen_paths:
            continue
        ordered.append(files_by_path[scaffold_file.path])
        seen_paths.add(scaffold_file.path)

    return ordered


def _merge_tech_stack(existing_stack: list[str]) -> list[str]:
    stack = list(existing_stack)
    stack_lookup = {item.casefold() for item in stack}
    for required_item in CRM_NEXT_MVP_STACK:
        if required_item.casefold() not in stack_lookup:
            stack.append(required_item)
            stack_lookup.add(required_item.casefold())
    return stack


def _package_json(app_name: str) -> str:
    payload = {
        "name": _package_name(app_name),
        "version": "0.1.0",
        "private": True,
        "scripts": {
            "dev": "next dev",
            "build": "next build",
            "start": "next start",
            "lint": "next lint",
        },
        "dependencies": {
            "@supabase/supabase-js": "^2.49.0",
            "next": "^15.0.0",
            "react": "^19.0.0",
            "react-dom": "^19.0.0",
        },
        "devDependencies": {
            "@types/node": "^22.0.0",
            "@types/react": "^19.0.0",
            "@types/react-dom": "^19.0.0",
            "autoprefixer": "^10.4.20",
            "postcss": "^8.4.49",
            "tailwindcss": "^3.4.17",
            "typescript": "^5.7.2",
        },
    }
    return f"{json.dumps(payload, indent=2)}\n"


def _package_name(app_name: str) -> str:
    normalized = "".join(
        character if character.isalnum() else "-" for character in app_name.casefold()
    )
    return "-".join(part for part in normalized.split("-") if part) or "crm-workspace"


def _tsconfig_json() -> str:
    payload = {
        "compilerOptions": {
            "target": "ES2017",
            "lib": ["dom", "dom.iterable", "esnext"],
            "allowJs": True,
            "skipLibCheck": True,
            "strict": True,
            "noEmit": True,
            "esModuleInterop": True,
            "module": "esnext",
            "moduleResolution": "bundler",
            "resolveJsonModule": True,
            "isolatedModules": True,
            "jsx": "preserve",
            "incremental": True,
            "plugins": [{"name": "next"}],
            "paths": {"@/*": ["./src/*"]},
        },
        "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
        "exclude": ["node_modules"],
    }
    return f"{json.dumps(payload, indent=2)}\n"


def _next_config_ts() -> str:
    return """import type { NextConfig } from "next";

const nextConfig: NextConfig = {};

export default nextConfig;
"""


def _postcss_config_js() -> str:
    return """module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
"""


def _tailwind_config_ts() -> str:
    return """import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111827",
        surface: "#f8fafc",
        brand: "#2563eb",
      },
    },
  },
  plugins: [],
};

export default config;
"""


def _layout_tsx(app_name: str, profile: CRMDomainProfile) -> str:
    app_name_json = json.dumps(app_name)
    description_json = json.dumps(
        f"CRM MVP for managing {profile.customer_plural.lower()}, "
        f"{profile.order_plural.lower()} and {profile.task_plural.lower()}."
    )
    return f"""import type {{ Metadata }} from "next";
import Link from "next/link";
import "./globals.css";

const appName = {app_name_json};
const appDescription = {description_json};

export const metadata: Metadata = {{
  title: appName,
  description: appDescription,
}};

const navItems = [
  {{ href: "/dashboard", label: "Dashboard" }},
  {{ href: "/customers", label: "Customers" }},
  {{ href: "/orders", label: "Orders" }},
  {{ href: "/tasks", label: "Tasks" }},
];

export default function RootLayout({{
  children,
}}: Readonly<{{
  children: React.ReactNode;
}}>) {{
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen bg-slate-100 text-slate-950">
          <header className="border-b border-slate-200 bg-white">
            <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-5 sm:flex-row">
              <Link href="/dashboard" className="text-xl font-bold tracking-tight">
                {{appName}}
              </Link>
              <nav className="flex flex-wrap gap-2">
                {{navItems.map((item) => (
                  <Link
                    key={{item.href}}
                    href={{item.href}}
                    className="rounded-md px-3 py-2 text-sm text-slate-600 hover:bg-slate-100"
                  >
                    {{item.label}}
                  </Link>
                ))}}
              </nav>
            </div>
          </header>
          <main className="mx-auto max-w-6xl px-4 py-8">{{children}}</main>
        </div>
      </body>
    </html>
  );
}}
"""


def _globals_css() -> str:
    return """@tailwind base;
@tailwind components;
@tailwind utilities;

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: Arial, Helvetica, sans-serif;
}
"""


def _root_page_tsx() -> str:
    return """import { redirect } from "next/navigation";

export default function HomePage() {
  redirect("/dashboard");
}
"""


def _schema_sql() -> str:
    return """create extension if not exists pgcrypto;

create table if not exists public.customers (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email text not null,
  phone text not null,
  segment text not null default 'Lead'
    check (segment in ('Lead', 'Active', 'VIP')),
  last_visit date,
  created_at timestamptz not null default now()
);

create table if not exists public.orders (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid references public.customers(id) on delete set null,
  customer_name text not null,
  service text not null,
  status text not null default 'Scheduled'
    check (status in ('Scheduled', 'In progress', 'Ready', 'Paid')),
  price numeric(10, 2) not null default 0,
  due_date date,
  created_at timestamptz not null default now()
);

create table if not exists public.tasks (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  owner text not null default 'Front desk',
  status text not null default 'Open'
    check (status in ('Open', 'Today', 'Done')),
  due_date date,
  created_at timestamptz not null default now()
);

alter table public.customers enable row level security;
alter table public.orders enable row level security;
alter table public.tasks enable row level security;

grant usage on schema public to anon, authenticated;
grant select, insert, update, delete on public.customers to anon, authenticated;
grant select, insert, update, delete on public.orders to anon, authenticated;
grant select, insert, update, delete on public.tasks to anon, authenticated;

drop policy if exists "crm customers read" on public.customers;
create policy "crm customers read"
  on public.customers for select
  using (true);

drop policy if exists "crm customers insert" on public.customers;
create policy "crm customers insert"
  on public.customers for insert
  with check (true);

drop policy if exists "crm customers update" on public.customers;
create policy "crm customers update"
  on public.customers for update
  using (true)
  with check (true);

drop policy if exists "crm customers delete" on public.customers;
create policy "crm customers delete"
  on public.customers for delete
  using (true);

drop policy if exists "crm orders read" on public.orders;
create policy "crm orders read"
  on public.orders for select
  using (true);

drop policy if exists "crm orders insert" on public.orders;
create policy "crm orders insert"
  on public.orders for insert
  with check (true);

drop policy if exists "crm orders update" on public.orders;
create policy "crm orders update"
  on public.orders for update
  using (true)
  with check (true);

drop policy if exists "crm orders delete" on public.orders;
create policy "crm orders delete"
  on public.orders for delete
  using (true);

drop policy if exists "crm tasks read" on public.tasks;
create policy "crm tasks read"
  on public.tasks for select
  using (true);

drop policy if exists "crm tasks insert" on public.tasks;
create policy "crm tasks insert"
  on public.tasks for insert
  with check (true);

drop policy if exists "crm tasks update" on public.tasks;
create policy "crm tasks update"
  on public.tasks for update
  using (true)
  with check (true);

drop policy if exists "crm tasks delete" on public.tasks;
create policy "crm tasks delete"
  on public.tasks for delete
  using (true);
"""


def _sample_data_sql(profile: CRMDomainProfile) -> str:
    sample_customer_name = _sql_literal(profile.sample_customer_name)
    sample_customer_email = _sql_literal(profile.sample_customer_email)
    sample_customer_phone = _sql_literal(profile.sample_customer_phone)
    sample_order_service = _sql_literal(profile.sample_order_service)
    sample_task_title = _sql_literal(profile.sample_task_title)
    sample_task_owner = _sql_literal(profile.sample_task_owner)
    return f"""-- Optional seed data for a {profile.key.replace("_", " ")} CRM.
insert into public.customers (name, email, phone, segment, last_visit)
values
  (
    {sample_customer_name},
    {sample_customer_email},
    {sample_customer_phone},
    'Active',
    current_date - interval '7 days'
  );

insert into public.orders (customer_name, service, status, price, due_date)
values
  (
    {sample_customer_name},
    {sample_order_service},
    'Scheduled',
    {profile.sample_order_price},
    current_date + interval '2 days'
  );

insert into public.tasks (title, owner, status, due_date)
values
  (
    {sample_task_title},
    {sample_task_owner},
    'Today',
    current_date
  );
"""


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _env_example() -> str:
    return """NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
"""


def _database_types_ts() -> str:
    return """export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export type Database = {
  public: {
    Tables: {
      customers: {
        Row: {
          id: string;
          name: string;
          email: string;
          phone: string;
          segment: "Lead" | "Active" | "VIP";
          last_visit: string | null;
          created_at: string;
        };
        Insert: {
          id?: string;
          name: string;
          email: string;
          phone: string;
          segment?: "Lead" | "Active" | "VIP";
          last_visit?: string | null;
          created_at?: string;
        };
        Update: {
          id?: string;
          name?: string;
          email?: string;
          phone?: string;
          segment?: "Lead" | "Active" | "VIP";
          last_visit?: string | null;
          created_at?: string;
        };
        Relationships: [];
      };
      orders: {
        Row: {
          id: string;
          customer_id: string | null;
          customer_name: string;
          service: string;
          status: "Scheduled" | "In progress" | "Ready" | "Paid";
          price: number;
          due_date: string | null;
          created_at: string;
        };
        Insert: {
          id?: string;
          customer_id?: string | null;
          customer_name: string;
          service: string;
          status?: "Scheduled" | "In progress" | "Ready" | "Paid";
          price?: number;
          due_date?: string | null;
          created_at?: string;
        };
        Update: {
          id?: string;
          customer_id?: string | null;
          customer_name?: string;
          service?: string;
          status?: "Scheduled" | "In progress" | "Ready" | "Paid";
          price?: number;
          due_date?: string | null;
          created_at?: string;
        };
        Relationships: [];
      };
      tasks: {
        Row: {
          id: string;
          title: string;
          owner: string;
          status: "Open" | "Today" | "Done";
          due_date: string | null;
          created_at: string;
        };
        Insert: {
          id?: string;
          title: string;
          owner?: string;
          status?: "Open" | "Today" | "Done";
          due_date?: string | null;
          created_at?: string;
        };
        Update: {
          id?: string;
          title?: string;
          owner?: string;
          status?: "Open" | "Today" | "Done";
          due_date?: string | null;
          created_at?: string;
        };
        Relationships: [];
      };
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
    Enums: Record<string, never>;
    CompositeTypes: Record<string, never>;
  };
};
"""


def _supabase_ts() -> str:
    return """import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import type { Database } from "./database.types";

let cachedClient: SupabaseClient<Database> | null = null;

export function getSupabaseClient(): SupabaseClient<Database> {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error(
      "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY."
    );
  }

  cachedClient ??= createClient<Database>(supabaseUrl, supabaseAnonKey);
  return cachedClient;
}

export type Customer = Database["public"]["Tables"]["customers"]["Row"];
export type CustomerInsert = Database["public"]["Tables"]["customers"]["Insert"];
export type CustomerUpdate = Database["public"]["Tables"]["customers"]["Update"];
export type Order = Database["public"]["Tables"]["orders"]["Row"];
export type OrderInsert = Database["public"]["Tables"]["orders"]["Insert"];
export type OrderUpdate = Database["public"]["Tables"]["orders"]["Update"];
export type Task = Database["public"]["Tables"]["tasks"]["Row"];
"""


def _customers_actions_ts() -> str:
    return """"use server";

import { revalidatePath } from "next/cache";
import {
  getSupabaseClient,
  type Customer,
  type CustomerInsert,
  type CustomerUpdate,
} from "@/lib/supabase";

const customerSegments = ["Lead", "Active", "VIP"] as const;
type CustomerSegment = (typeof customerSegments)[number];

function formString(formData: FormData, key: string): string {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function normalizeSegment(value: string): CustomerSegment {
  return customerSegments.includes(value as CustomerSegment)
    ? (value as CustomerSegment)
    : "Lead";
}

function normalizeDate(value: string): string | null {
  return value.length > 0 ? value : null;
}

export async function listCustomers(): Promise<Customer[]> {
  const supabase = getSupabaseClient();
  const { data, error } = await supabase
    .from("customers")
    .select("*")
    .order("created_at", { ascending: false });

  if (error) {
    throw new Error(`Failed to load customers: ${error.message}`);
  }

  return data ?? [];
}

export async function createCustomer(formData: FormData): Promise<void> {
  const payload: CustomerInsert = {
    name: formString(formData, "name"),
    email: formString(formData, "email"),
    phone: formString(formData, "phone"),
    segment: normalizeSegment(formString(formData, "segment")),
    last_visit: normalizeDate(formString(formData, "lastVisit")),
  };

  if (!payload.name || !payload.email || !payload.phone) {
    throw new Error("Name, email and phone are required.");
  }

  const supabase = getSupabaseClient();
  const { error } = await supabase.from("customers").insert(payload);

  if (error) {
    throw new Error(`Failed to create customer: ${error.message}`);
  }

  revalidatePath("/customers");
  revalidatePath("/dashboard");
}

export async function updateCustomer(formData: FormData): Promise<void> {
  const id = formString(formData, "id");
  const payload: CustomerUpdate = {
    name: formString(formData, "name"),
    email: formString(formData, "email"),
    phone: formString(formData, "phone"),
    segment: normalizeSegment(formString(formData, "segment")),
    last_visit: normalizeDate(formString(formData, "lastVisit")),
  };

  if (!id || !payload.name || !payload.email || !payload.phone) {
    throw new Error("Customer id, name, email and phone are required.");
  }

  const supabase = getSupabaseClient();
  const { error } = await supabase.from("customers").update(payload).eq("id", id);

  if (error) {
    throw new Error(`Failed to update customer: ${error.message}`);
  }

  revalidatePath("/customers");
  revalidatePath("/dashboard");
}

export async function deleteCustomer(formData: FormData): Promise<void> {
  const id = formString(formData, "id");

  if (!id) {
    throw new Error("Customer id is required.");
  }

  const supabase = getSupabaseClient();
  const { error } = await supabase.from("customers").delete().eq("id", id);

  if (error) {
    throw new Error(`Failed to delete customer: ${error.message}`);
  }

  revalidatePath("/customers");
  revalidatePath("/dashboard");
}
"""


def _orders_actions_ts() -> str:
    return """"use server";

import { revalidatePath } from "next/cache";
import {
  getSupabaseClient,
  type Order,
  type OrderInsert,
  type OrderUpdate,
} from "@/lib/supabase";

const orderStatuses = ["Scheduled", "In progress", "Ready", "Paid"] as const;
type OrderStatus = (typeof orderStatuses)[number];

function formString(formData: FormData, key: string): string {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function normalizeStatus(value: string): OrderStatus {
  return orderStatuses.includes(value as OrderStatus)
    ? (value as OrderStatus)
    : "Scheduled";
}

function normalizeDate(value: string): string | null {
  return value.length > 0 ? value : null;
}

function normalizePrice(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
}

export async function listOrders(): Promise<Order[]> {
  const supabase = getSupabaseClient();
  const { data, error } = await supabase
    .from("orders")
    .select("*")
    .order("created_at", { ascending: false });

  if (error) {
    throw new Error(`Failed to load orders: ${error.message}`);
  }

  return data ?? [];
}

export async function createOrder(formData: FormData): Promise<void> {
  const payload: OrderInsert = {
    customer_id: formString(formData, "customerId") || null,
    customer_name: formString(formData, "customerName"),
    service: formString(formData, "service"),
    status: normalizeStatus(formString(formData, "status")),
    price: normalizePrice(formString(formData, "price")),
    due_date: normalizeDate(formString(formData, "dueDate")),
  };

  if (!payload.customer_name || !payload.service) {
    throw new Error("Customer name and service are required.");
  }

  const supabase = getSupabaseClient();
  const { error } = await supabase.from("orders").insert(payload);

  if (error) {
    throw new Error(`Failed to create order: ${error.message}`);
  }

  revalidatePath("/orders");
  revalidatePath("/dashboard");
}

export async function updateOrderStatus(formData: FormData): Promise<void> {
  const id = formString(formData, "id");
  const payload: OrderUpdate = {
    status: normalizeStatus(formString(formData, "status")),
  };

  if (!id) {
    throw new Error("Order id is required.");
  }

  const supabase = getSupabaseClient();
  const { error } = await supabase.from("orders").update(payload).eq("id", id);

  if (error) {
    throw new Error(`Failed to update order: ${error.message}`);
  }

  revalidatePath("/orders");
  revalidatePath("/dashboard");
}

export async function deleteOrder(formData: FormData): Promise<void> {
  const id = formString(formData, "id");

  if (!id) {
    throw new Error("Order id is required.");
  }

  const supabase = getSupabaseClient();
  const { error } = await supabase.from("orders").delete().eq("id", id);

  if (error) {
    throw new Error(`Failed to delete order: ${error.message}`);
  }

  revalidatePath("/orders");
  revalidatePath("/dashboard");
}
"""


def _tasks_actions_ts() -> str:
    return """"use server";

import { getSupabaseClient, type Task } from "@/lib/supabase";

export async function listTasks(): Promise<Task[]> {
  const supabase = getSupabaseClient();
  const { data, error } = await supabase
    .from("tasks")
    .select("*")
    .order("created_at", { ascending: false });

  if (error) {
    throw new Error(`Failed to load tasks: ${error.message}`);
  }

  return data ?? [];
}
"""


def _dashboard_page_tsx(profile: CRMDomainProfile) -> str:
    template = """import { listCustomers } from "@/app/customers/actions";
import { listOrders } from "@/app/orders/actions";
import { listTasks } from "@/app/tasks/actions";

export const dynamic = "force-dynamic";

function formatPrice(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);
}

export default async function DashboardPage() {
  const [customers, orders, tasks] = await Promise.all([
    listCustomers(),
    listOrders(),
    listTasks(),
  ]);
  const openOrders = orders.filter((order) => order.status !== "Paid");
  const todayTasks = tasks.filter((task) => task.status === "Today");
  const revenue = orders.reduce((total, order) => total + Number(order.price), 0);
  const metricCards = [
    {
      label: "Total __CUSTOMER_PLURAL__",
      value: customers.length,
      caption: "Stored in Supabase",
    },
    {
      label: "Total __ORDER_PLURAL__",
      value: orders.length,
      caption: "All Supabase __ORDER_SINGULAR_LOWER__ records",
    },
    {
      label: "Open __ORDER_PLURAL__",
      value: openOrders.length,
      caption: "Scheduled or in progress",
    },
    {
      label: "__TASK_PLURAL__ Today",
      value: todayTasks.length,
      caption: `${tasks.length} __TASK_PLURAL_LOWER__ in database`,
    },
  ];

  return (
    <div className="space-y-8">
      <section>
        <p className="text-sm font-medium uppercase tracking-wide text-blue-600">
          Dashboard
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">__DASHBOARD_TITLE__</h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          __DASHBOARD_DESCRIPTION__
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        {metricCards.map((metric) => (
          <article key={metric.label} className="rounded-lg border border-slate-200 bg-white p-5">
            <p className="text-sm font-medium text-slate-500">{metric.label}</p>
            <p className="mt-3 text-3xl font-bold">{metric.value}</p>
            <p className="mt-1 text-sm text-slate-500">{metric.caption}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-[1fr_280px]">
        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="text-lg font-semibold">Latest __ORDER_PLURAL_LOWER__</h2>
          <div className="mt-4 grid gap-3">
            {orders.length === 0 ? (
              <p className="rounded-md bg-slate-50 p-4 text-sm text-slate-500">
                No __ORDER_PLURAL_LOWER__ yet. Add the first
                __ORDER_SINGULAR_LOWER__ from the __ORDER_PLURAL__ page.
              </p>
            ) : (
              orders.slice(0, 5).map((order) => (
                <div key={order.id} className="rounded-md bg-slate-50 p-4">
                  <div>
                    <p className="font-medium">{order.customer_name}</p>
                    <p className="text-sm text-slate-500">{order.service}</p>
                  </div>
                  <span className="rounded-full bg-blue-100 px-3 py-1 text-sm text-blue-700">
                    {order.status}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <p className="text-sm font-medium text-slate-500">Revenue tracked</p>
          <p className="mt-3 text-3xl font-bold">{formatPrice(revenue)}</p>
          <p className="mt-1 text-sm text-slate-500">
            Sum of all __ORDER_SINGULAR_LOWER__ prices in Supabase.
          </p>
        </div>
      </section>
    </div>
  );
}
"""
    return (
        template.replace("__DASHBOARD_TITLE__", profile.dashboard_title)
        .replace("__DASHBOARD_DESCRIPTION__", profile.dashboard_description)
        .replace("__CUSTOMER_PLURAL__", profile.customer_plural)
        .replace("__ORDER_PLURAL__", profile.order_plural)
        .replace("__ORDER_PLURAL_LOWER__", profile.order_plural.lower())
        .replace("__ORDER_SINGULAR_LOWER__", profile.order_singular.lower())
        .replace("__TASK_PLURAL__", profile.task_plural)
        .replace("__TASK_PLURAL_LOWER__", profile.task_plural.lower())
    )


def _customers_page_tsx(profile: CRMDomainProfile) -> str:
    template = """import {
  createCustomer,
  deleteCustomer,
  listCustomers,
  updateCustomer,
} from "./actions";

export const dynamic = "force-dynamic";

const segmentOptions = ["Lead", "Active", "VIP"];

export default async function CustomersPage() {
  const customers = await listCustomers();

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium uppercase tracking-wide text-blue-600">
              __CUSTOMER_PLURAL__
            </p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight">__CUSTOMER_PAGE_TITLE__</h1>
          </div>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium">
            {customers.length} __CUSTOMER_PLURAL_LOWER__
          </span>
        </div>

        <div className="mt-6 grid gap-4">
          {customers.length === 0 ? (
            <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-500">
              No __CUSTOMER_PLURAL_LOWER__ yet. Add the first
              __CUSTOMER_SINGULAR_LOWER__ to Supabase.
            </p>
          ) : (
            customers.map((customer) => (
              <article key={customer.id} className="rounded-lg border border-slate-200 p-4">
                <form action={updateCustomer} className="grid gap-3 md:grid-cols-2">
                  <input type="hidden" name="id" value={customer.id} />
                  <label className="grid gap-1 text-sm font-medium">
                    __CUSTOMER_SINGULAR__ name
                    <input
                      name="name"
                      required
                      defaultValue={customer.name}
                      className="rounded-md border border-slate-300 px-3 py-2 font-normal"
                    />
                  </label>
                  <label className="grid gap-1 text-sm font-medium">
                    Email
                    <input
                      name="email"
                      required
                      type="email"
                      defaultValue={customer.email}
                      className="rounded-md border border-slate-300 px-3 py-2 font-normal"
                    />
                  </label>
                  <label className="grid gap-1 text-sm font-medium">
                    Phone
                    <input
                      name="phone"
                      required
                      defaultValue={customer.phone}
                      className="rounded-md border border-slate-300 px-3 py-2 font-normal"
                    />
                  </label>
                  <label className="grid gap-1 text-sm font-medium">
                    Segment
                    <select
                      name="segment"
                      defaultValue={customer.segment}
                      className="rounded-md border border-slate-300 px-3 py-2 font-normal"
                    >
                      {segmentOptions.map((segment) => (
                        <option key={segment} value={segment}>
                          {segment}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="grid gap-1 text-sm font-medium md:col-span-2">
                    Last visit
                    <input
                      name="lastVisit"
                      type="date"
                      defaultValue={customer.last_visit ?? ""}
                      className="rounded-md border border-slate-300 px-3 py-2 font-normal"
                    />
                  </label>
                  <button className="rounded-md bg-slate-900 px-4 py-2 font-semibold text-white">
                    Save changes
                  </button>
                </form>
                <form action={deleteCustomer} className="mt-3">
                  <input type="hidden" name="id" value={customer.id} />
                  <button className="text-sm font-medium text-red-600">
                    Delete __CUSTOMER_SINGULAR_LOWER__
                  </button>
                </form>
              </article>
            ))
          )}
        </div>
      </section>

      <aside className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-lg font-semibold">Add __CUSTOMER_SINGULAR_LOWER__</h2>
        <form action={createCustomer} className="mt-4 grid gap-4">
          <label className="grid gap-1 text-sm font-medium">
            __CUSTOMER_SINGULAR__ name
            <input
              name="name"
              required
              className="rounded-md border border-slate-300 px-3 py-2 font-normal"
              placeholder="__SAMPLE_CUSTOMER_NAME__"
            />
          </label>
          <label className="grid gap-1 text-sm font-medium">
            Email
            <input
              name="email"
              type="email"
              required
              className="rounded-md border border-slate-300 px-3 py-2 font-normal"
              placeholder="__SAMPLE_CUSTOMER_EMAIL__"
            />
          </label>
          <label className="grid gap-1 text-sm font-medium">
            Phone
            <input
              name="phone"
              required
              className="rounded-md border border-slate-300 px-3 py-2 font-normal"
              placeholder="__SAMPLE_CUSTOMER_PHONE__"
            />
          </label>
          <label className="grid gap-1 text-sm font-medium">
            Segment
            <select
              name="segment"
              defaultValue="Lead"
              className="rounded-md border border-slate-300 px-3 py-2 font-normal"
            >
              {segmentOptions.map((segment) => (
                <option key={segment} value={segment}>
                  {segment}
                </option>
              ))}
            </select>
          </label>
          <button className="rounded-md bg-blue-600 px-4 py-2 font-semibold text-white">
            Add __CUSTOMER_SINGULAR_LOWER__
          </button>
        </form>
      </aside>
    </div>
  );
}
"""
    return (
        template.replace("__CUSTOMER_PLURAL__", profile.customer_plural)
        .replace("__CUSTOMER_PLURAL_LOWER__", profile.customer_plural.lower())
        .replace("__CUSTOMER_SINGULAR__", profile.customer_singular)
        .replace("__CUSTOMER_SINGULAR_LOWER__", profile.customer_singular.lower())
        .replace("__CUSTOMER_PAGE_TITLE__", profile.customer_page_title)
        .replace("__SAMPLE_CUSTOMER_NAME__", profile.sample_customer_name)
        .replace("__SAMPLE_CUSTOMER_EMAIL__", profile.sample_customer_email)
        .replace("__SAMPLE_CUSTOMER_PHONE__", profile.sample_customer_phone)
    )


def _orders_page_tsx(profile: CRMDomainProfile) -> str:
    template = """import {
  createOrder,
  deleteOrder,
  listOrders,
  updateOrderStatus,
} from "./actions";

const statusStyles = {
  Scheduled: "bg-amber-100 text-amber-700",
  "In progress": "bg-blue-100 text-blue-700",
  Ready: "bg-emerald-100 text-emerald-700",
  Paid: "bg-slate-100 text-slate-700",
};

const statusOptions = ["Scheduled", "In progress", "Ready", "Paid"];

function formatPrice(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);
}

export const dynamic = "force-dynamic";

export default async function OrdersPage() {
  const orders = await listOrders();

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <p className="text-sm font-medium uppercase tracking-wide text-blue-600">
          Orders
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">__ORDER_PAGE_TITLE__</h1>
        <p className="mt-2 text-slate-600">
          Create, update and close real Supabase __ORDER_PLURAL_LOWER__.
        </p>

        <div className="mt-6 grid gap-4">
          {orders.length === 0 ? (
            <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-500">
              No __ORDER_PLURAL_LOWER__ yet. Create the first __ORDER_SINGULAR_LOWER__.
            </p>
          ) : (
            orders.map((order) => (
              <article key={order.id} className="rounded-lg border border-slate-200 p-4">
                <div className="flex flex-col justify-between gap-3 sm:flex-row">
                  <div>
                    <p className="text-lg font-semibold">{order.customer_name}</p>
                    <p className="text-sm text-slate-500">{order.service}</p>
                  </div>
                  <span className={`rounded-full px-3 py-1 text-sm ${statusStyles[order.status]}`}>
                    {order.status}
                  </span>
                </div>
                <div className="mt-4 grid gap-2 text-sm text-slate-600 sm:grid-cols-3">
                  <span>Order #{order.id.slice(0, 8)}</span>
                  <span>Date: {order.due_date ?? "Not scheduled"}</span>
                  <span>Price: {formatPrice(Number(order.price))}</span>
                </div>
                <div className="mt-4 flex flex-wrap gap-3">
                  <form action={updateOrderStatus} className="flex gap-2">
                    <input type="hidden" name="id" value={order.id} />
                    <select
                      name="status"
                      defaultValue={order.status}
                      className="rounded-md border border-slate-300 px-3 py-2 text-sm"
                    >
                      {statusOptions.map((status) => (
                        <option key={status} value={status}>
                          {status}
                        </option>
                      ))}
                    </select>
                    <button className="rounded-md bg-slate-900 px-3 py-2 text-sm text-white">
                      Update
                    </button>
                  </form>
                  <form action={deleteOrder}>
                    <input type="hidden" name="id" value={order.id} />
                    <button className="px-3 py-2 text-sm font-medium text-red-600">
                      Delete
                    </button>
                  </form>
                </div>
              </article>
            ))
          )}
        </div>
      </section>

      <aside className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-lg font-semibold">Create order</h2>
        <form action={createOrder} className="mt-4 grid gap-4">
          <label className="grid gap-1 text-sm font-medium">
            __CUSTOMER_SINGULAR__ name
            <input
              name="customerName"
              required
              className="rounded-md border border-slate-300 px-3 py-2 font-normal"
              placeholder="__SAMPLE_CUSTOMER_NAME__"
            />
          </label>
          <label className="grid gap-1 text-sm font-medium">
            __SERVICE_SINGULAR__
            <input
              name="service"
              required
              className="rounded-md border border-slate-300 px-3 py-2 font-normal"
              placeholder="__SAMPLE_ORDER_SERVICE__"
            />
          </label>
          <label className="grid gap-1 text-sm font-medium">
            Price
            <input
              name="price"
              type="number"
              min="0"
              step="0.01"
              className="rounded-md border border-slate-300 px-3 py-2 font-normal"
              placeholder="__SAMPLE_ORDER_PRICE__"
            />
          </label>
          <label className="grid gap-1 text-sm font-medium">
            Due date
            <input
              name="dueDate"
              type="date"
              className="rounded-md border border-slate-300 px-3 py-2 font-normal"
            />
          </label>
          <label className="grid gap-1 text-sm font-medium">
            Status
            <select
              name="status"
              defaultValue="Scheduled"
              className="rounded-md border border-slate-300 px-3 py-2 font-normal"
            >
              {statusOptions.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <button className="rounded-md bg-blue-600 px-4 py-2 font-semibold text-white">
            Add __ORDER_SINGULAR_LOWER__
          </button>
        </form>
      </aside>
    </div>
  );
}
"""
    return (
        template.replace("__ORDER_PAGE_TITLE__", profile.order_page_title)
        .replace("__ORDER_PLURAL_LOWER__", profile.order_plural.lower())
        .replace("__ORDER_SINGULAR_LOWER__", profile.order_singular.lower())
        .replace("__CUSTOMER_SINGULAR__", profile.customer_singular)
        .replace("__SERVICE_SINGULAR__", profile.service_singular)
        .replace("__SAMPLE_CUSTOMER_NAME__", profile.sample_customer_name)
        .replace("__SAMPLE_ORDER_SERVICE__", profile.sample_order_service)
        .replace("__SAMPLE_ORDER_PRICE__", profile.sample_order_price)
    )


def _tasks_page_tsx(profile: CRMDomainProfile) -> str:
    template = """import { listTasks } from "./actions";

const statusStyles = {
  Open: "bg-slate-100 text-slate-700",
  Today: "bg-blue-100 text-blue-700",
  Done: "bg-emerald-100 text-emerald-700",
};

export const dynamic = "force-dynamic";

export default async function TasksPage() {
  const tasks = await listTasks();

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <p className="text-sm font-medium uppercase tracking-wide text-blue-600">
        Tasks
      </p>
      <h1 className="mt-2 text-3xl font-bold tracking-tight">__TASK_PAGE_TITLE__</h1>
      <p className="mt-2 text-slate-600">
        __TASK_PAGE_DESCRIPTION__
      </p>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        {tasks.length === 0 ? (
          <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-500 md:col-span-3">
            No __TASK_PLURAL_LOWER__ yet. Add rows to the tasks table in Supabase to fill the board.
          </p>
        ) : (
          tasks.map((task) => (
            <article key={task.id} className="rounded-lg border border-slate-200 p-4">
              <span className={`rounded-full px-3 py-1 text-xs ${statusStyles[task.status]}`}>
                {task.status}
              </span>
              <h2 className="mt-4 font-semibold">{task.title}</h2>
              <p className="mt-2 text-sm text-slate-500">__TEAM_SINGULAR__: {task.owner}</p>
              <p className="text-sm text-slate-500">
                Due: {task.due_date ?? "Not scheduled"}
              </p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
"""
    return (
        template.replace("__TASK_PAGE_TITLE__", profile.task_page_title)
        .replace("__TASK_PAGE_DESCRIPTION__", profile.task_page_description)
        .replace("__TASK_PLURAL_LOWER__", profile.task_plural.lower())
        .replace("__TEAM_SINGULAR__", profile.team_singular)
    )
