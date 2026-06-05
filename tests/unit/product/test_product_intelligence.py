from vuls.llm.schemas import ProjectBrief
from vuls.product_intelligence import build_product_intelligence


def test_product_brief_for_dentistry_crm_contains_product_planning_sections() -> None:
    intelligence = build_product_intelligence(
        raw_idea="Create a CRM for a dentistry clinic",
        brief=ProjectBrief(
            title="Dentistry CRM",
            goal="Create a CRM for a dentistry clinic",
            target_users=["clinic owner", "receptionist", "dentist"],
            must_have_features=["patients", "appointments", "treatments"],
            language_code="en",
        ),
        selected_template_key="crm",
    )

    brief = intelligence.product_brief

    assert brief.product_name == "Dentistry CRM"
    assert brief.target_audience
    assert brief.user_problems
    assert brief.value_proposition
    assert "patients" in _joined(brief.core_features)
    assert "appointments" in _joined(brief.mvp_scope)
    assert brief.monetization
    assert brief.risks
    assert brief.success_metrics
    assert intelligence.product_memory.domain == "dentistry"


def test_feature_prioritization_splits_features_by_mvp_priority() -> None:
    intelligence = build_product_intelligence(
        raw_idea="Build an AI fitness trainer",
        brief=ProjectBrief(
            title="AI Fitness Trainer",
            goal="Build an AI fitness trainer",
            target_users=["fitness members", "trainers"],
            must_have_features=["workout plans", "progress tracking", "AI recommendations"],
            language_code="en",
        ),
        selected_template_key="ai_agent",
    )

    prioritization = intelligence.feature_prioritization

    assert "workout plans" in prioritization.must_have
    assert "progress tracking" in prioritization.must_have
    assert prioritization.should_have
    assert prioritization.could_have
    assert prioritization.future


def test_project_roadmap_has_mvp_growth_and_scale_phases() -> None:
    intelligence = build_product_intelligence(
        raw_idea="Create a SaaS for task management",
        brief=ProjectBrief(
            title="Task Management SaaS",
            goal="Create a SaaS for task management",
            target_users=["team leads", "operators"],
            must_have_features=["tasks", "projects", "collaboration"],
            language_code="en",
        ),
        selected_template_key="saas",
    )

    phases = {phase.name: phase for phase in intelligence.roadmap.phases}

    assert set(phases) == {"Phase 1 - MVP", "Phase 2 - Growth", "Phase 3 - Scale"}
    assert phases["Phase 1 - MVP"].goals
    assert phases["Phase 2 - Growth"].features
    assert phases["Phase 3 - Scale"].metrics


def test_product_memory_preserves_generation_context_and_decisions() -> None:
    intelligence = build_product_intelligence(
        raw_idea="Create a CRM for a dental clinic",
        brief=ProjectBrief(
            title="Dental Clinic CRM",
            goal="Create a CRM for a dental clinic",
            target_users=["clinic owner"],
            must_have_features=["patients", "appointments"],
            language_code="en",
        ),
        selected_template_key="crm",
    )

    memory = intelligence.product_memory

    assert memory.source_idea == "Create a CRM for a dental clinic"
    assert memory.selected_template == "crm"
    assert memory.domain == "dentistry"
    assert "Template selected: crm" in memory.generator_decisions
    assert "Domain detected: dentistry" in memory.generator_decisions
    assert memory.change_history


def test_fitness_idea_uses_fitness_specific_terminology() -> None:
    intelligence = build_product_intelligence(
        raw_idea="AI fitness trainer for gym members",
        brief=ProjectBrief(
            title="AI Fitness Trainer",
            goal="AI fitness trainer for gym members",
            target_users=["members", "trainers"],
            must_have_features=["workouts", "memberships"],
            language_code="en",
        ),
        selected_template_key="ai_agent",
    )

    content = _joined(
        [
            intelligence.product_brief.value_proposition,
            *intelligence.product_brief.core_features,
            *intelligence.product_brief.mvp_scope,
        ]
    )

    assert "workout" in content
    assert "trainers" in content or "trainer" in content
    assert "membership" in content or "members" in content


def test_dentistry_crm_does_not_inherit_car_wash_terms() -> None:
    intelligence = build_product_intelligence(
        raw_idea="CRM for dentistry",
        brief=ProjectBrief(
            title="Dentistry CRM",
            goal="CRM for dentistry",
            target_users=["dentists"],
            must_have_features=["patients"],
            language_code="en",
        ),
        selected_template_key="crm",
    )

    serialized = intelligence.model_dump_json().lower()

    assert "car wash" not in serialized
    assert "premium wash" not in serialized
    assert "vehicle" not in serialized


def _joined(values: list[str]) -> str:
    return " ".join(values).lower()
