import pytest

from vuls.templates.registry import TemplateRegistry


@pytest.mark.parametrize(
    ("intent", "expected_key"),
    [
        ("Create a CRM for a small coffee shop with customers and orders", "crm"),
        ("Build a subscription SaaS for teams with billing and workspaces", "saas"),
        ("Make a two sided marketplace for tutors and students", "marketplace"),
        ("Create an AI agent that triages support tickets and uses tools", "ai_agent"),
        ("Build an operations dashboard with KPIs, charts and analytics", "dashboard"),
    ],
)
def test_template_auto_detection_selects_expected_template(
    intent: str,
    expected_key: str,
) -> None:
    selection = TemplateRegistry().select_template(intent)

    assert selection.selected_key == expected_key
    assert selection.confidence >= 0.5
    assert selection.needs_clarification is False
    assert selection.clarification_question is None


def test_template_auto_detection_does_not_guess_when_confidence_is_low() -> None:
    selection = TemplateRegistry().select_template("I have an idea for something useful")

    assert selection.selected_key is None
    assert selection.confidence < 0.5
    assert selection.needs_clarification is True
    assert selection.clarification_question == (
        "Which product type fits best: CRM, SaaS, Marketplace, AI Agent or Dashboard?"
    )


def test_template_auto_detection_returns_scores_for_all_templates() -> None:
    selection = TemplateRegistry().select_template("dashboard for marketplace sales analytics")

    assert set(selection.scores) == {"crm", "saas", "marketplace", "ai_agent", "dashboard"}
    assert selection.scores["dashboard"] > 0
    assert selection.scores["marketplace"] > 0
