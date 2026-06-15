from vuls.reference_analysis import ReferenceInput, analyze_references
from vuls.reference_image_intelligence import (
    ReferenceImageInput,
    ReferenceImageItem,
    analyze_reference_images,
)
from vuls.reference_product_intelligence import (
    ReferenceProductInput,
    analyze_reference_product,
)


def test_reference_product_intelligence_detects_saas_workspace_from_screenshot() -> None:
    image_analysis = analyze_reference_images(
        ReferenceImageInput(
            images=[
                ReferenceImageItem(
                    filename="teamly-workspace.png",
                    width=1440,
                    height=900,
                    caption=(
                        "Teamly SaaS workspace dashboard with sidebar navigation, "
                        "documents, team members, billing, settings, search, and notifications."
                    ),
                    tags=["saas", "workspace", "documents", "team", "billing", "settings"],
                )
            ],
            user_intent="Build something like this workspace product.",
            platform="web",
        )
    )
    reference_analysis = analyze_references(
        ReferenceInput(
            image_analysis=image_analysis,
            user_intent="Teamly workspace screenshot",
            platform="web",
        )
    )

    analysis = analyze_reference_product(
        ReferenceProductInput(
            image_analysis=image_analysis,
            reference_analysis=reference_analysis,
            user_intent="Teamly workspace screenshot",
            platform="web",
        )
    )

    assert analysis.product_type == "SaaS Workspace"
    assert analysis.confidence >= 0.7
    assert _feature_names(analysis) >= {
        "documents",
        "team management",
        "billing",
        "settings",
        "sidebar",
    }
    assert "Workspace" in analysis.suggested_product_structure
    assert "Documents" in analysis.suggested_product_structure
    assert "Team Members" in analysis.suggested_product_structure
    assert "Billing" in analysis.suggested_product_structure
    assert any(
        pattern.pattern_name == "left navigation"
        for pattern in analysis.detected_patterns
    )


def test_reference_product_intelligence_detects_crm() -> None:
    analysis = analyze_reference_product(
        ReferenceProductInput(
            user_intent=(
                "CRM dashboard screenshot with customers, deals, pipeline table, "
                "reports, analytics, and settings."
            ),
            platform="web",
        )
    )

    assert analysis.product_type == "CRM"
    assert {"dashboard", "analytics", "settings"} <= _feature_names(analysis)
    assert analysis.suggested_product_structure == [
        "Dashboard",
        "Customers",
        "Deals",
        "Reports",
        "Settings",
    ]


def test_reference_product_intelligence_detects_learning_platform() -> None:
    analysis = analyze_reference_product(
        ReferenceProductInput(
            user_intent=(
                "Learning app screenshot with courses, lessons, student progress, "
                "achievements, profile, notifications, and onboarding."
            ),
            platform="web",
        )
    )

    assert analysis.product_type == "Learning Platform"
    assert {"profile", "notifications"} <= _feature_names(analysis)
    assert "Lessons" in analysis.suggested_product_structure
    assert "Progress" in analysis.suggested_product_structure
    assert any(
        pattern.pattern_name == "onboarding flow"
        for pattern in analysis.detected_patterns
    )


def test_reference_product_intelligence_detects_dashboard() -> None:
    analysis = analyze_reference_product(
        ReferenceProductInput(
            user_intent=(
                "Operations dashboard screenshot with analytics cards, metrics, "
                "reports, filters, table layout, and sidebar."
            ),
            platform="web",
        )
    )

    assert analysis.product_type == "Dashboard"
    assert {"dashboard", "analytics", "sidebar"} <= _feature_names(analysis)
    assert "Analytics" in analysis.suggested_product_structure
    assert any(
        pattern.pattern_name == "dashboard-first design"
        for pattern in analysis.detected_patterns
    )


def test_reference_product_intelligence_no_reference_fallback() -> None:
    analysis = analyze_reference_product(ReferenceProductInput())

    assert analysis.product_type == "Unknown"
    assert analysis.confidence == 0
    assert analysis.detected_features == []
    assert analysis.detected_patterns == []
    assert analysis.suggested_product_structure == []
    assert "No reference product signals" in analysis.reasoning


def _feature_names(analysis: object) -> set[str]:
    return {feature.name for feature in analysis.detected_features}
