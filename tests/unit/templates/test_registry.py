from pathlib import Path

import pytest

from vuls.templates.registry import EXPECTED_TEMPLATE_KEYS, TemplateRegistry
from vuls.templates.renderer import render_template_context


def test_registry_loads_exactly_the_v1_template_catalog() -> None:
    registry = TemplateRegistry()

    templates = registry.load_all()

    assert [template.key for template in templates] == list(EXPECTED_TEMPLATE_KEYS)


@pytest.mark.parametrize("template_key", EXPECTED_TEMPLATE_KEYS)
def test_each_template_declares_required_metadata(template_key: str) -> None:
    template = TemplateRegistry().get(template_key)

    assert template.key == template_key
    assert template.name
    assert template.description
    assert template.category
    assert template.default_pages
    assert template.default_entities
    assert template.default_roles
    assert template.keywords
    assert template.i18n_keys
    assert "overview" in template.readme_sections
    assert "setup" in template.readme_sections


@pytest.mark.parametrize("template_key", EXPECTED_TEMPLATE_KEYS)
def test_each_template_has_prompt_and_file_blueprints(template_key: str) -> None:
    template = TemplateRegistry().get(template_key)

    assert template.prompt_markdown.startswith("#")
    assert template.file_blueprint.files
    assert all(file.path for file in template.file_blueprint.files)
    assert all(file.purpose for file in template.file_blueprint.files)


def test_crm_template_declares_next_app_router_mvp_blueprint() -> None:
    template = TemplateRegistry().get("crm")
    paths = {file.path for file in template.file_blueprint.files}

    assert {
        "package.json",
        "tsconfig.json",
        "tailwind.config.ts",
        "schema.sql",
        "env.example",
        "src/app/layout.tsx",
        "src/app/globals.css",
        "src/app/dashboard/page.tsx",
        "src/app/customers/actions.ts",
        "src/app/customers/page.tsx",
        "src/app/orders/actions.ts",
        "src/app/orders/page.tsx",
        "src/app/tasks/actions.ts",
        "src/app/tasks/page.tsx",
        "src/lib/database.types.ts",
        "src/lib/supabase.ts",
    }.issubset(paths)
    assert "deals" not in template.default_pages


def test_registry_validation_reports_no_catalog_errors() -> None:
    registry = TemplateRegistry()

    assert registry.validate_catalog() == []


def test_registry_rejects_unknown_template_key() -> None:
    registry = TemplateRegistry()

    with pytest.raises(KeyError, match="unknown"):
        registry.get("unknown")


def test_renderer_returns_llm_ready_template_context_without_calling_llm() -> None:
    template = TemplateRegistry().get("crm")

    context = render_template_context(
        template,
        user_intent="Create a CRM for a small coffee shop",
        project_memory=["User prefers FastAPI"],
    )

    assert context == {
        "template_key": "crm",
        "name": "CRM",
        "description": template.description,
        "category": "business_operations",
        "default_pages": template.default_pages,
        "default_entities": template.default_entities,
        "default_roles": template.default_roles,
        "i18n_keys": template.i18n_keys,
        "readme_sections": template.readme_sections,
        "prompt_markdown": template.prompt_markdown,
        "file_blueprint": [file.model_dump(mode="json") for file in template.file_blueprint.files],
        "user_intent": "Create a CRM for a small coffee shop",
        "project_memory": ["User prefers FastAPI"],
    }


def test_registry_can_load_from_explicit_catalog_path() -> None:
    catalog_path = Path("src/vuls/templates/catalog")

    assert TemplateRegistry(catalog_path).get("dashboard").name == "Dashboard"
