from vuls.design_intelligence import (
    DesignInput,
    build_design_contract,
    design_contract_prompt_items,
    load_design_contract,
)
from vuls.llm.schemas import ProjectBrief
from vuls.product_intelligence import ProductBriefDocument, build_product_intelligence


def test_fitness_prompt_creates_premium_fitness_design_contract() -> None:
    intelligence = build_product_intelligence(
        raw_idea="Хочу приложение для фитнес-клуба",
        brief=ProjectBrief(
            title="Fitness Club App",
            goal="Хочу приложение для фитнес-клуба",
            target_users=["club owner", "trainers", "members"],
            must_have_features=["memberships", "classes", "progress tracking"],
            language_code="ru",
        ),
        selected_template_key="crm",
    )

    contract = build_design_contract(
        DesignInput(
            product_brief=intelligence.product_brief,
            domain=intelligence.product_memory.domain,
            user_prompt="Хочу приложение для фитнес-клуба",
            platform="telegram_mini_app",
        )
    )

    assert contract.visual_archetype.key == "gamified_reward_interface"
    assert "energetic" in contract.product_emotion
    assert "member progress" in contract.hero_object_strategy.lower()
    assert "generic crm" not in contract.open_design_brief.prompt.lower()
    assert "fitness" in contract.open_design_brief.prompt.lower()
    assert contract.visual_system.color_system
    assert contract.component_rules.primary_components
    assert contract.ux_rules


def test_references_are_inspiration_signals_not_templates() -> None:
    contract = build_design_contract(
        DesignInput(
            product_brief=_brief("AI Habit Coach"),
            domain="fitness",
            user_prompt="Create a habit and fitness motivation app",
            references=[
                "Duolingo streak celebration",
                "Apple Fitness rings",
            ],
            desired_emotion="playful but premium",
            platform="mobile",
        )
    )

    prompt = contract.open_design_brief.prompt.lower()
    negative_constraints = " ".join(contract.open_design_brief.negative_constraints).lower()

    assert contract.open_design_brief.inspiration_signals == [
        "Duolingo streak celebration",
        "Apple Fitness rings",
    ]
    assert "reference examples are inspiration signals, not templates" in prompt
    assert "do not copy" in negative_constraints
    assert "do not create a duolingo template" in negative_constraints
    assert "do not create an apple template" in negative_constraints


def test_telegram_mini_app_contract_is_compact_and_thumb_first() -> None:
    contract = build_design_contract(
        DesignInput(
            product_brief=_brief("Dental Clinic CRM"),
            domain="dentistry",
            user_prompt="CRM for dentistry",
            platform="telegram_mini_app",
        )
    )

    combined = " ".join(
        [
            contract.screen_composition,
            *contract.component_rules.interaction_rules,
            *contract.ux_rules,
        ]
    ).lower()

    assert contract.visual_archetype.key == "clean_medical_dashboard"
    assert "telegram mini app" in combined
    assert "thumb" in combined
    assert "compact" in combined


def test_load_design_contract_builds_contract_for_legacy_payload() -> None:
    contract = load_design_contract(
        payload={},
        product_brief=_brief("Logistics Control"),
        domain="logistics",
        user_prompt="Operations dashboard for truck delivery routes",
        platform="web",
    )

    assert contract.visual_archetype.key == "dark_technical_control_center"
    assert contract.open_design_brief.prompt
    assert design_contract_prompt_items(contract)


def _brief(name: str) -> ProductBriefDocument:
    return ProductBriefDocument(
        product_name=name,
        target_audience=["operators"],
        user_problems=["Operators need a clearer daily workflow."],
        value_proposition=f"{name} helps operators make better decisions.",
        core_features=["dashboard", "tasks", "progress tracking"],
        mvp_scope=["dashboard", "tasks"],
        monetization=["subscription"],
        risks=["The MVP must avoid overbuilding."],
        success_metrics=["weekly active users"],
    )
