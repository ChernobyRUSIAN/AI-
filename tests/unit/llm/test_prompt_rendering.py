from vuls.llm.prompts import (
    build_brief_normalization_prompt,
    build_project_manifest_prompt,
)
from vuls.llm.schemas import BriefNormalizationRequest, ProjectBrief, ProjectManifestRequest
from vuls.templates.registry import TemplateRegistry


def test_brief_normalization_prompt_includes_user_idea_language_and_memory() -> None:
    request = BriefNormalizationRequest(
        user_idea="Create a CRM for a coffee shop",
        language_code="en",
        memory_context={
            "user": ["User prefers Python and FastAPI."],
            "project": ["The app is for owner and staff."],
        },
    )

    messages = build_brief_normalization_prompt(request)

    assert [message.role for message in messages] == ["system", "user"]
    assert "normalize raw product ideas" in messages[0].content
    assert "Create a CRM for a coffee shop" in messages[1].content
    assert '"language_code": "en"' in messages[1].content
    assert "User prefers Python and FastAPI." in messages[1].content
    assert "Return only JSON" in messages[1].content


def test_project_manifest_prompt_includes_template_rules_and_output_shape() -> None:
    template = TemplateRegistry().get("crm")
    request = ProjectManifestRequest(
        template=template,
        brief=ProjectBrief(
            title="Coffee CRM",
            goal="Build a CRM for a small coffee shop.",
            target_users=["owner", "staff"],
            must_have_features=["customers", "orders", "tasks"],
            language_code="en",
        ),
        memory_context={"project": ["Selected CRM template."]},
    )

    messages = build_project_manifest_prompt(request)

    assert [message.role for message in messages] == ["system", "user"]
    assert "generate complete project file manifests" in messages[0].content
    assert "CRM Template Prompt" in messages[1].content
    assert "Coffee CRM" in messages[1].content
    assert "default_pages" in messages[1].content
    assert "default_entities" in messages[1].content
    assert "readme_summary" in messages[1].content
    assert "env_vars" in messages[1].content


def test_crm_manifest_prompt_requires_real_nextjs_mvp_pages() -> None:
    template = TemplateRegistry().get("crm")
    request = ProjectManifestRequest(
        template=template,
        brief=ProjectBrief(
            title="Car Wash CRM",
            goal="Build a CRM for a car wash.",
            target_users=["owner", "staff"],
            must_have_features=["dashboard", "customers", "orders", "tasks"],
            language_code="en",
        ),
    )

    prompt = build_project_manifest_prompt(request)[1].content

    assert "Next.js App Router" in prompt
    assert "TypeScript" in prompt
    assert "Tailwind" in prompt
    assert "src/app/dashboard/page.tsx" in prompt
    assert "src/app/customers/page.tsx" in prompt
    assert "src/app/orders/page.tsx" in prompt
    assert "src/app/tasks/page.tsx" in prompt
    assert "schema.sql" in prompt
    assert "env.example" in prompt
    assert "src/lib/supabase.ts" in prompt
    assert "Do not create placeholder pages" in prompt
    assert "Never import from next/router" in prompt
    assert "next/navigation" in prompt
    assert "Supabase" in prompt
    assert "CRUD" in prompt
    assert "customer list" in prompt
    assert "add-customer form" in prompt
    assert "order status" in prompt
    assert "src/lib/mock-data.ts" not in prompt
