from vuls.integrations.open_design import (
    product_intelligence_to_open_design_input,
    render_open_design_brief,
    render_react_tailwind_artifact,
)


def test_product_intelligence_to_open_design_input_uses_domain_fields() -> None:
    payload = product_intelligence_to_open_design_input(
        {
            "title": "CRM for Dentistry",
            "domain": "Dental clinic CRM",
            "audience": ["clinic owner", "front desk"],
            "workflows": ["follow up treatment plans"],
            "entities": ["patient", "appointment"],
            "metrics": ["recall due"],
            "routes": ["/patients"],
            "visual_direction": "clinical",
        }
    )

    assert payload.slug == "crm-for-dentistry"
    assert payload.domain == "Dental clinic CRM"
    assert payload.audience == ("clinic owner", "front desk")
    assert payload.workflows == ("follow up treatment plans",)
    assert payload.entities == ("patient", "appointment")
    assert payload.routes == ("/patients",)


def test_render_open_design_brief_targets_nextjs_tailwind() -> None:
    payload = product_intelligence_to_open_design_input({"title": "CRM for Fitness Club"})

    brief = render_open_design_brief(payload)

    assert "# CRM for Fitness Club" in brief
    assert "Next.js App Router" in brief
    assert "Tailwind-compatible" in brief


def test_open_design_input_prefers_design_contract_prompt_when_available() -> None:
    payload = product_intelligence_to_open_design_input(
        {
            "title": "Fitness Club App",
            "domain": "fitness",
            "design_contract": {
                "visual_archetype": {
                    "key": "gamified_reward_interface",
                    "label": "Gamified reward interface",
                    "rationale": "Fitness needs motivation loops.",
                },
                "product_emotion": "energetic, motivating, premium",
                "hero_object_strategy": "Member progress pulse",
                "screen_composition": "Mobile-first command surface",
                "visual_hierarchy": "Progress before operations",
                "surface_model": "Layered premium cards",
                "visual_system": {
                    "color_system": "Energetic contrast",
                    "typography_direction": "Bold progress numerics",
                    "spacing_radius_system": "Compact touch rhythm",
                    "motion_direction": "Subtle reward motion",
                },
                "component_rules": {
                    "primary_components": ["progress hero", "member action queue"],
                    "interaction_rules": ["Thumb-first primary action"],
                    "forbidden_patterns": ["Do not copy a reference screen."],
                },
                "ux_rules": ["Prioritize member motivation over generic tables."],
                "open_design_brief": {
                    "prompt": (
                        "Create a fitness command center. Reference examples are "
                        "inspiration signals, not templates."
                    ),
                    "inspiration_signals": ["reward loops"],
                    "negative_constraints": ["Do not copy any reference UI."],
                },
            },
        }
    )

    brief = render_open_design_brief(payload)

    assert "Create a fitness command center" in payload.visual_direction
    assert "Reference examples are inspiration signals, not templates" in brief
    assert "Do not copy any reference UI" in brief


def test_render_react_tailwind_artifact_contains_reusable_component() -> None:
    payload = product_intelligence_to_open_design_input({"title": "CRM for Fitness Club"})

    component = render_react_tailwind_artifact(payload)

    assert "export default function VulsCrmPage" in component
    assert "CrmPageProps" in component
    assert "className=\"min-h-screen bg-slate-50" in component
    assert "const routes" in component
