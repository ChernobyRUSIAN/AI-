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


def test_open_design_brief_includes_reference_analysis_section_when_available() -> None:
    payload = product_intelligence_to_open_design_input(
        {
            "title": "Drone Control",
            "domain": "drone operations",
            "reference_analysis": {
                "mood_signals": [],
                "composition_signals": [
                    {
                        "signal_type": "dark_technical_control",
                        "value": "Use a focused technical command surface.",
                        "confidence": 0.9,
                        "rationale": "Reference language mentions telemetry and control.",
                    }
                ],
                "visual_quality_signals": [
                    {
                        "signal_type": "premium_depth",
                        "value": "Use depth and layered control surfaces.",
                        "confidence": 0.7,
                        "rationale": "Reference language mentions premium layers.",
                    }
                ],
                "interaction_signals": [],
                "platform_signals": [],
                "negative_constraints": [
                    "Reference examples are inspiration signals, not templates.",
                    "Do not copy layouts, brand assets, or proprietary UI.",
                ],
                "summary": "References suggest a premium technical control direction.",
            },
        }
    )

    brief = render_open_design_brief(payload)

    assert "## Reference Analysis" in brief
    assert "dark_technical_control" in brief
    assert "premium_depth" in brief
    assert "Reference examples are inspiration signals, not templates" in brief
    assert "Do not copy layouts, brand assets, or proprietary UI" in brief


def test_open_design_brief_includes_reference_image_intelligence_section_when_available() -> None:
    payload = product_intelligence_to_open_design_input(
        {
            "title": "Reward App",
            "domain": "fitness",
            "reference_image_analysis": {
                "composition_signals": [
                    {
                        "signal_type": "strong_focal_object",
                        "value": "Use a product-specific focal object.",
                        "confidence": 0.8,
                        "rationale": "Image metadata points to a hero object.",
                    }
                ],
                "color_signals": [],
                "density_signals": [],
                "platform_signals": [
                    {
                        "signal_type": "mobile_portrait_reference",
                        "value": "Use mobile portrait ergonomics.",
                        "confidence": 0.9,
                        "rationale": "Image aspect ratio is portrait.",
                    }
                ],
                "quality_signals": [
                    {
                        "signal_type": "premium_depth_reference",
                        "value": "Use premium depth.",
                        "confidence": 0.7,
                        "rationale": "Image metadata mentions premium glow.",
                    }
                ],
                "negative_constraints": [
                    "Image references are visual quality signals, not copy targets.",
                    (
                        "Do not copy logos, brand assets, mascots, characters, "
                        "proprietary layouts, or recognizable identity."
                    ),
                ],
                "summary": "Image metadata suggests mobile premium reward UI.",
            },
        }
    )

    brief = render_open_design_brief(payload)

    assert "## Reference Image Intelligence" in brief
    assert "strong_focal_object" in brief
    assert "mobile_portrait_reference" in brief
    assert "premium_depth_reference" in brief
    assert "Image references are visual quality signals, not copy targets" in brief
    assert "Do not copy logos, brand assets, mascots, characters" in brief


def test_open_design_brief_omits_reference_image_section_for_legacy_payload() -> None:
    payload = product_intelligence_to_open_design_input({"title": "Legacy CRM"})

    brief = render_open_design_brief(payload)

    assert "## Reference Image Intelligence" not in brief


def test_render_react_tailwind_artifact_contains_reusable_component() -> None:
    payload = product_intelligence_to_open_design_input({"title": "CRM for Fitness Club"})

    component = render_react_tailwind_artifact(payload)

    assert "export default function VulsCrmPage" in component
    assert "CrmPageProps" in component
    assert "className=\"min-h-screen bg-slate-50" in component
    assert "const routes" in component
