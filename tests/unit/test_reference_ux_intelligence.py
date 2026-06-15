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
from vuls.reference_ux_intelligence import (
    ReferenceUXInput,
    analyze_reference_ux,
    reference_ux_analysis_prompt_items,
)


def test_reference_ux_intelligence_detects_saas_workspace_flow() -> None:
    analysis = _ux_analysis_for(
        caption=(
            "Teamly SaaS workspace dashboard with sidebar navigation, documents, "
            "team members, billing, settings, search, and notifications."
        ),
        tags=["saas", "workspace", "documents", "team", "billing", "settings"],
        user_intent="Use this Teamly workspace screenshot as product reference.",
    )

    assert analysis.primary_goal == "Manage team knowledge"
    assert _screen_names(analysis) >= {"Workspace", "Documents", "Team", "Billing"}
    assert [step.screen_name for step in analysis.user_flows][:4] == [
        "Login",
        "Workspace",
        "Document",
        "Editor",
    ]
    assert any(step.action == "Share with team" for step in analysis.user_flows)
    assert any(
        pattern.pattern == "sidebar-first"
        for pattern in analysis.navigation_patterns
    )
    assert analysis.retention_loop == ["Create", "Collaborate", "Update", "Return"]


def test_reference_ux_intelligence_detects_crm_flow() -> None:
    analysis = _ux_analysis_for(
        caption=(
            "CRM dashboard screenshot with customers, deals, pipeline table, reports, "
            "analytics, search, and settings."
        ),
        tags=["crm", "customers", "deals", "pipeline", "reports"],
        user_intent="CRM reference with customer and deal workflow.",
    )

    assert analysis.primary_goal == "Manage customers and deals"
    assert _screen_names(analysis) >= {"Dashboard", "Customers", "Deals", "Reports"}
    assert [step.screen_name for step in analysis.user_flows] == [
        "Dashboard",
        "Leads",
        "Customer",
        "Deal",
        "Report",
    ]
    assert analysis.retention_loop == [
        "Capture leads",
        "Manage deals",
        "Track results",
        "Return",
    ]


def test_reference_ux_intelligence_detects_learning_platform_flow() -> None:
    analysis = _ux_analysis_for(
        caption=(
            "Learning app screenshot with courses, lessons, quiz, student progress, "
            "achievements, profile, notifications, and onboarding."
        ),
        tags=["learning", "courses", "lessons", "quiz", "progress", "achievements"],
        user_intent="Learning platform reference for lessons and progress.",
    )

    assert analysis.primary_goal == "Learn lessons and track progress"
    assert _screen_names(analysis) >= {"Lessons", "Progress", "Achievements", "Profile"}
    assert [step.screen_name for step in analysis.user_flows] == [
        "Home",
        "Lesson",
        "Quiz",
        "Result",
        "Progress",
    ]
    assert analysis.onboarding_flow == ["Sign up", "Choose course", "Start lesson"]
    assert analysis.retention_loop == ["Learn", "Progress", "Achievement", "Return"]


def test_reference_ux_intelligence_detects_dashboard_navigation() -> None:
    analysis = _ux_analysis_for(
        caption=(
            "Operations dashboard screenshot with analytics cards, metrics, reports, "
            "filters, table layout, and sidebar."
        ),
        tags=["dashboard", "analytics", "metrics", "reports", "filters"],
        user_intent="Operations dashboard reference.",
    )

    assert analysis.primary_goal == "Monitor metrics and act on insights"
    assert _screen_names(analysis) >= {"Dashboard", "Analytics", "Reports"}
    assert any(
        pattern.pattern == "dashboard-first"
        for pattern in analysis.navigation_patterns
    )
    assert any(
        pattern.pattern == "sidebar-first"
        for pattern in analysis.navigation_patterns
    )


def test_reference_ux_prompt_items_include_flow_navigation_and_retention() -> None:
    analysis = _ux_analysis_for(
        caption=(
            "Teamly SaaS workspace dashboard with sidebar navigation, documents, "
            "team members, billing, settings, and notifications."
        ),
        tags=["saas", "workspace", "documents", "team", "billing", "settings"],
        user_intent="Teamly reference.",
    )

    prompt_items = reference_ux_analysis_prompt_items(analysis)

    assert any("Reference UX Intelligence:" in item for item in prompt_items)
    assert any("UX user flow:" in item and "Login -> Workspace" in item for item in prompt_items)
    assert any(
        "UX navigation patterns:" in item and "sidebar-first" in item
        for item in prompt_items
    )
    assert any(
        "UX retention loop:" in item and "Create -> Collaborate" in item
        for item in prompt_items
    )


def test_reference_ux_intelligence_no_reference_fallback() -> None:
    analysis = analyze_reference_ux(ReferenceUXInput())

    assert analysis.primary_goal == "Unknown"
    assert analysis.user_goals == []
    assert analysis.user_flows == []
    assert analysis.core_screens == []
    assert analysis.navigation_patterns == []
    assert analysis.onboarding_flow == []
    assert analysis.retention_loop == []
    assert "No reference UX signals" in analysis.reasoning


def _ux_analysis_for(
    *,
    caption: str,
    tags: list[str],
    user_intent: str,
):
    image_analysis = analyze_reference_images(
        ReferenceImageInput(
            images=[
                ReferenceImageItem(
                    filename="reference.png",
                    width=1440,
                    height=900,
                    caption=caption,
                    tags=tags,
                )
            ],
            user_intent=user_intent,
            platform="web",
        )
    )
    reference_analysis = analyze_references(
        ReferenceInput(
            image_analysis=image_analysis,
            user_intent=user_intent,
            platform="web",
        )
    )
    product_analysis = analyze_reference_product(
        ReferenceProductInput(
            image_analysis=image_analysis,
            reference_analysis=reference_analysis,
            user_intent=user_intent,
            platform="web",
        )
    )
    return analyze_reference_ux(
        ReferenceUXInput(
            image_analysis=image_analysis,
            reference_analysis=reference_analysis,
            reference_product_analysis=product_analysis,
            user_intent=user_intent,
            platform="web",
        )
    )


def _screen_names(analysis: object) -> set[str]:
    return {screen.name for screen in analysis.core_screens}
