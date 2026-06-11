# ruff: noqa: E501
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

JsonValue = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject = dict[str, JsonValue]


class OpenDesignAPIError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, body: object = None) -> None:
        super().__init__(message)
        self.status = status
        self.body = body


@dataclass(frozen=True)
class OpenDesignInput:
    slug: str
    title: str
    domain: str
    audience: tuple[str, ...]
    workflows: tuple[str, ...]
    entities: tuple[str, ...]
    metrics: tuple[str, ...]
    routes: tuple[str, ...]
    visual_direction: str
    reference_image_analysis: JsonObject | None
    reference_analysis: JsonObject | None


@dataclass(frozen=True)
class OpenDesignPublishResult:
    project_id: str
    project_response: JsonObject
    files_response: JsonObject
    artifact_paths: tuple[str, ...]


class OpenDesignClient:
    def __init__(self, base_url: str, *, timeout_seconds: float = 15.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def health(self) -> JsonObject:
        return self._request_json("GET", "/api/health")

    def daemon_status(self) -> JsonObject:
        return self._request_json("GET", "/api/daemon/status")

    def create_project(self, project_id: str, payload: OpenDesignInput) -> JsonObject:
        body: JsonObject = {
            "id": project_id,
            "name": payload.title,
            "designSystemId": "default",
            "skipDiscoveryBrief": True,
            "metadata": {
                "kind": "prototype",
                "platform": "responsive",
                "skipDiscoveryBrief": True,
                "source": "vuls-open-design-spike",
                "domain": payload.domain,
            },
        }
        return self._request_json("POST", "/api/projects", body)

    def create_artifact(
        self,
        project_id: str,
        *,
        path: str,
        content: str,
        artifact_manifest: JsonObject | None = None,
    ) -> JsonObject:
        body: JsonObject = {
            "name": path,
            "content": content,
            "artifact": True,
            "overwrite": False,
        }
        if artifact_manifest is not None:
            body["artifactManifest"] = artifact_manifest
        return self._request_json("POST", f"/api/projects/{quote(project_id)}/files", body)

    def list_files(self, project_id: str) -> JsonObject:
        return self._request_json("GET", f"/api/projects/{quote(project_id)}/files")

    def read_file_text(self, project_id: str, path: str) -> str:
        encoded_path = "/".join(quote(segment) for segment in path.split("/"))
        return self._request_text("GET", f"/api/projects/{quote(project_id)}/files/{encoded_path}")

    def _request_json(
        self,
        method: str,
        path: str,
        body: JsonObject | None = None,
    ) -> JsonObject:
        text = self._request_text(method, path, body)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise OpenDesignAPIError(f"Open Design returned non-JSON for {path}") from exc
        if not isinstance(parsed, dict):
            raise OpenDesignAPIError(f"Open Design returned a non-object JSON body for {path}")
        return cast(JsonObject, parsed)

    def _request_text(
        self,
        method: str,
        path: str,
        body: JsonObject | None = None,
    ) -> str:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(
            f"{self._base_url}{path}",
            data=data,
            method=method,
            headers={
                "accept": "application/json, text/html;q=0.9, */*;q=0.1",
                "content-type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                return cast(str, response.read().decode("utf-8"))
        except HTTPError as exc:
            error_text = exc.read().decode("utf-8", errors="replace")
            raise OpenDesignAPIError(
                f"Open Design API {method} {path} failed with HTTP {exc.code}",
                status=exc.code,
                body=_parse_error_body(error_text),
            ) from exc
        except URLError as exc:
            raise OpenDesignAPIError(f"Could not reach Open Design daemon: {exc.reason}") from exc


def product_intelligence_to_open_design_input(data: dict[str, object]) -> OpenDesignInput:
    title = _string(data, "title", fallback="CRM Workspace")
    domain = _string(data, "domain", fallback=title)
    design_direction = _design_contract_visual_direction(data)
    return OpenDesignInput(
        slug=_slug(title),
        title=title,
        domain=domain,
        audience=_string_tuple(data, "audience", fallback=("owner", "manager", "staff")),
        workflows=_string_tuple(data, "workflows", fallback=("review dashboard", "manage customers")),
        entities=_string_tuple(
            data,
            "entities",
            fallback=("customer", "appointment", "deal", "task", "note"),
        ),
        metrics=_string_tuple(data, "metrics", fallback=("new leads", "open tasks", "monthly revenue")),
        routes=_string_tuple(
            data,
            "routes",
            fallback=("/dashboard", "/customers", "/deals", "/tasks", "/settings"),
        ),
        visual_direction=design_direction
        or _string(
            data,
            "visual_direction",
            fallback="Operational SaaS UI with calm contrast, dense tables, and clear action states.",
        ),
        reference_image_analysis=_reference_image_analysis_from_data(data),
        reference_analysis=_reference_analysis_from_data(data),
    )


def render_open_design_brief(payload: OpenDesignInput) -> str:
    return "\n".join(
        [
            f"# {payload.title}",
            "",
            "## Product Intelligence",
            f"- Domain: {payload.domain}",
            f"- Audience: {', '.join(payload.audience)}",
            f"- Visual direction: {payload.visual_direction}",
            "",
            *_render_reference_image_analysis_section(payload.reference_image_analysis),
            *_render_reference_analysis_section(payload.reference_analysis),
            "## Core Workflows",
            *[f"- {item}" for item in payload.workflows],
            "",
            "## Domain Entities",
            *[f"- {item}" for item in payload.entities],
            "",
            "## Metrics",
            *[f"- {item}" for item in payload.metrics],
            "",
            "## Target Routes",
            *[f"- {item}" for item in payload.routes],
            "",
            "## Generation Target",
            "Create a CRM UI suitable for a Next.js App Router application. Prefer React 18,",
            "TypeScript, Tailwind-compatible utility classes, accessible controls, and reusable",
            "dashboard/card/table sections.",
            "",
        ]
    )


def render_crm_html_artifact(payload: OpenDesignInput) -> str:
    workflow_cards = "\n".join(
        f"<article><strong>{escape(item)}</strong><span>Ready for staff handoff</span></article>"
        for item in payload.workflows[:4]
    )
    metric_cards = "\n".join(
        f"<div class=\"metric\"><b>{escape(item.title())}</b><span>{index * 17 + 24}</span></div>"
        for index, item in enumerate(payload.metrics[:4], start=1)
    )
    routes = "\n".join(f"<li>{escape(route)}</li>" for route in payload.routes)
    entities = "\n".join(f"<tr><td>{escape(entity.title())}</td><td>Active</td><td>Owner</td></tr>" for entity in payload.entities[:6])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(payload.title)}</title>
  <style>
    :root {{ color-scheme: light; --ink:#132238; --muted:#607086; --line:#dbe4ef; --blue:#2563eb; --green:#16a34a; --bg:#f5f7fb; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif; background:var(--bg); color:var(--ink); }}
    main {{ max-width:1180px; margin:0 auto; padding:30px; }}
    header {{ display:flex; align-items:center; justify-content:space-between; gap:20px; margin-bottom:24px; }}
    h1 {{ margin:0; font-size:34px; letter-spacing:0; }}
    .eyebrow {{ color:var(--blue); font-weight:800; font-size:13px; text-transform:uppercase; }}
    .shell {{ display:grid; grid-template-columns:220px 1fr; gap:22px; }}
    nav, section, article, .metric {{ background:white; border:1px solid var(--line); border-radius:8px; box-shadow:0 8px 24px rgba(19,34,56,.06); }}
    nav {{ padding:18px; }}
    nav ul {{ list-style:none; padding:0; margin:14px 0 0; display:grid; gap:10px; }}
    nav li {{ padding:10px 12px; border-radius:6px; background:#f8fafc; color:var(--muted); }}
    .grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin-bottom:18px; }}
    .metric {{ padding:16px; }}
    .metric b {{ display:block; color:var(--muted); font-size:12px; }}
    .metric span {{ display:block; font-size:28px; font-weight:850; margin-top:8px; }}
    section {{ padding:20px; margin-bottom:18px; }}
    .workflow {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }}
    article {{ padding:16px; min-height:94px; }}
    article span {{ display:block; color:var(--muted); margin-top:10px; }}
    table {{ width:100%; border-collapse:collapse; margin-top:12px; overflow:hidden; }}
    th, td {{ padding:13px 10px; border-bottom:1px solid var(--line); text-align:left; }}
    th {{ color:var(--muted); font-size:12px; text-transform:uppercase; }}
    .actions {{ display:flex; gap:10px; }}
    button {{ border:0; border-radius:7px; padding:10px 14px; background:var(--blue); color:white; font-weight:750; }}
    button.secondary {{ background:#e0f2fe; color:#075985; }}
    @media (max-width: 820px) {{ .shell {{ grid-template-columns:1fr; }} .grid, .workflow {{ grid-template-columns:1fr; }} header {{ align-items:flex-start; flex-direction:column; }} }}
  </style>
</head>
<body>
  <main>
    <header>
      <div><div class="eyebrow">Vuls + Open Design CRM</div><h1>{escape(payload.title)}</h1><p>{escape(payload.visual_direction)}</p></div>
      <div class="actions"><button>New customer</button><button class="secondary">Review tasks</button></div>
    </header>
    <div class="shell">
      <nav><strong>{escape(payload.domain)}</strong><ul>{routes}</ul></nav>
      <div>
        <div class="grid">{metric_cards}</div>
        <section><h2>Priority workflows</h2><div class="workflow">{workflow_cards}</div></section>
        <section><h2>Domain data model</h2><table><thead><tr><th>Entity</th><th>Status</th><th>Role</th></tr></thead><tbody>{entities}</tbody></table></section>
      </div>
    </div>
  </main>
</body>
</html>
"""


def render_react_tailwind_artifact(payload: OpenDesignInput) -> str:
    workflows = json.dumps(list(payload.workflows), indent=2)
    metrics = json.dumps(list(payload.metrics), indent=2)
    entities = json.dumps(list(payload.entities), indent=2)
    routes = json.dumps(list(payload.routes), indent=2)
    return f"""type CrmPageProps = {{
  title?: string;
}};

const workflows = {workflows} as const;
const metrics = {metrics} as const;
const entities = {entities} as const;
const routes = {routes} as const;

export default function VulsCrmPage({{ title = {json.dumps(payload.title)} }}: CrmPageProps) {{
  return (
    <main className="min-h-screen bg-slate-50 px-6 py-8 text-slate-950">
      <header className="mx-auto flex max-w-7xl flex-col gap-4 border-b border-slate-200 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-blue-700">Vuls + Open Design CRM</p>
          <h1 className="mt-2 text-4xl font-semibold tracking-normal">{{title}}</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">{escape(payload.visual_direction)}</p>
        </div>
        <div className="flex gap-2">
          <button className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm">New customer</button>
          <button className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700">Review tasks</button>
        </div>
      </header>
      <div className="mx-auto mt-6 grid max-w-7xl gap-6 lg:grid-cols-[240px_1fr]">
        <aside className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm font-semibold text-slate-900">{escape(payload.domain)}</p>
          <nav className="mt-4 grid gap-2">
            {{routes.map((route) => (
              <a key={{route}} className="rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600" href={{route}}>
                {{route}}
              </a>
            ))}}
          </nav>
        </aside>
        <section className="grid gap-6">
          <div className="grid gap-3 md:grid-cols-4">
            {{metrics.map((metric, index) => (
              <article key={{metric}} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                <p className="text-xs font-medium uppercase text-slate-500">{{metric}}</p>
                <p className="mt-2 text-3xl font-semibold">{{24 + index * 17}}</p>
              </article>
            ))}}
          </div>
          <div className="grid gap-4 xl:grid-cols-2">
            {{workflows.map((workflow) => (
              <article key={{workflow}} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="text-lg font-semibold">{{workflow}}</h2>
                <p className="mt-2 text-sm text-slate-600">Operational flow ready for manager and staff handoff.</p>
              </article>
            ))}}
          </div>
          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr><th className="px-4 py-3">Entity</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Owner</th></tr>
              </thead>
              <tbody>
                {{entities.map((entity) => (
                  <tr key={{entity}} className="border-t border-slate-100">
                    <td className="px-4 py-3 font-medium">{{entity}}</td><td className="px-4 py-3">Active</td><td className="px-4 py-3">Manager</td>
                  </tr>
                ))}}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}}
"""


def publish_product_intelligence(
    client: OpenDesignClient,
    product_intelligence: dict[str, object],
    *,
    project_id: str | None = None,
) -> OpenDesignPublishResult:
    payload = product_intelligence_to_open_design_input(product_intelligence)
    resolved_project_id = project_id or f"vuls-{payload.slug}-{_timestamp()}"
    project_response = client.create_project(resolved_project_id, payload)
    artifact_paths = (
        "product-intelligence.md",
        "artifact/index.html",
        "react/VulsCrmPage.tsx",
    )
    client.create_artifact(
        resolved_project_id,
        path=artifact_paths[0],
        content=render_open_design_brief(payload),
    )
    client.create_artifact(
        resolved_project_id,
        path=artifact_paths[1],
        content=render_crm_html_artifact(payload),
    )
    client.create_artifact(
        resolved_project_id,
        path=artifact_paths[2],
        content=render_react_tailwind_artifact(payload),
        artifact_manifest={
            "version": 1,
            "kind": "react-component",
            "title": f"{payload.title} React handoff",
            "entry": artifact_paths[2],
            "renderer": "react-component",
            "status": "complete",
            "exports": ["jsx", "html", "zip"],
            "metadata": {
                "source": "vuls-open-design-spike",
                "nextjsCompatible": True,
                "tailwindCompatible": True,
            },
        },
    )
    return OpenDesignPublishResult(
        project_id=resolved_project_id,
        project_response=project_response,
        files_response=client.list_files(resolved_project_id),
        artifact_paths=artifact_paths,
    )


def _parse_error_body(text: str) -> object:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _string(data: dict[str, object], key: str, *, fallback: str) -> str:
    value = data.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else fallback


def _string_tuple(
    data: dict[str, object],
    key: str,
    *,
    fallback: tuple[str, ...],
) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list):
        return fallback
    strings = tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
    return strings or fallback


def _design_contract_visual_direction(data: dict[str, object]) -> str | None:
    contract = data.get("design_contract")
    if not isinstance(contract, Mapping):
        return None
    open_design_brief = contract.get("open_design_brief")
    if not isinstance(open_design_brief, Mapping):
        return None
    prompt = open_design_brief.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return None

    parts = [prompt.strip()]
    negative_constraints = _strings_from_value(open_design_brief.get("negative_constraints"))
    if negative_constraints:
        parts.append(f"Negative constraints: {'; '.join(negative_constraints)}.")
    inspiration_signals = _strings_from_value(open_design_brief.get("inspiration_signals"))
    if inspiration_signals:
        parts.append(f"Inspiration signals: {'; '.join(inspiration_signals)}.")
    return " ".join(parts)


def _reference_analysis_from_data(data: dict[str, object]) -> JsonObject | None:
    value = data.get("reference_analysis")
    if not isinstance(value, Mapping):
        return None
    return cast(JsonObject, dict(value))


def _reference_image_analysis_from_data(data: dict[str, object]) -> JsonObject | None:
    value = data.get("reference_image_analysis")
    if not isinstance(value, Mapping):
        return None
    return cast(JsonObject, dict(value))


def _render_reference_image_analysis_section(analysis: JsonObject | None) -> list[str]:
    if analysis is None:
        return []

    lines = [
        "## Reference Image Intelligence",
        f"- Summary: {_json_string(analysis.get('summary'), fallback='Image reference signals provided.')}",
    ]
    lines.extend(_signal_lines("Composition signals", analysis.get("composition_signals")))
    lines.extend(_signal_lines("Color signals", analysis.get("color_signals")))
    lines.extend(_signal_lines("Density signals", analysis.get("density_signals")))
    lines.extend(_signal_lines("Platform signals", analysis.get("platform_signals")))
    lines.extend(_signal_lines("Quality signals", analysis.get("quality_signals")))

    negative_constraints = _strings_from_value(analysis.get("negative_constraints"))
    if negative_constraints:
        lines.append("- Constraints:")
        lines.extend(f"  - {item}" for item in negative_constraints)
    lines.append("")
    return lines


def _render_reference_analysis_section(analysis: JsonObject | None) -> list[str]:
    if analysis is None:
        return []

    lines = [
        "## Reference Analysis",
        f"- Summary: {_json_string(analysis.get('summary'), fallback='Reference signals provided.')}",
    ]
    lines.extend(_signal_lines("Mood signals", analysis.get("mood_signals")))
    lines.extend(_signal_lines("Composition signals", analysis.get("composition_signals")))
    lines.extend(_signal_lines("Quality bar", analysis.get("visual_quality_signals")))
    lines.extend(_signal_lines("Interaction signals", analysis.get("interaction_signals")))
    lines.extend(_signal_lines("Platform signals", analysis.get("platform_signals")))

    negative_constraints = _strings_from_value(analysis.get("negative_constraints"))
    if negative_constraints:
        lines.append("- Negative constraints:")
        lines.extend(f"  - {item}" for item in negative_constraints)
    lines.append("")
    return lines


def _signal_lines(label: str, value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    lines: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        signal_type = _json_string(item.get("signal_type"), fallback="reference_signal")
        signal_value = _json_string(item.get("value"), fallback="Use as abstract inspiration.")
        rationale = _json_string(item.get("rationale"), fallback="")
        if not lines:
            lines.append(f"- {label}:")
        detail = f"  - {signal_type}: {signal_value}"
        if rationale:
            detail = f"{detail} ({rationale})"
        lines.append(detail)
    return lines


def _json_string(value: object, *, fallback: str) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else fallback


def _strings_from_value(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized[:64] or "crm-workspace"


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d%H%M%S")
