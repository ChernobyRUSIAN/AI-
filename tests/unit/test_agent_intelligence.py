import pytest

from vuls.agent_intelligence import (
    AgentExecutionContext,
    AgentExecutionResult,
    AgentRegistry,
    AgentRole,
    AgentTask,
    AgentWorkflow,
    WorkflowStep,
    agent_memory_prompt_items,
    execute_agent_workflow,
    plan_agent_workflow,
)
from vuls.design_intelligence import DesignInput, build_design_contract
from vuls.llm.schemas import ProjectBrief
from vuls.product_intelligence import build_product_intelligence
from vuls.reference_analysis import ReferenceInput, analyze_references


def test_default_registry_contains_vuls_architect_agent() -> None:
    registry = AgentRegistry.default()

    architect = registry.get(AgentRole.VULS_ARCHITECT)

    assert architect.id == "vuls_architect"
    assert architect.role is AgentRole.VULS_ARCHITECT
    assert architect.name == "Vuls Architect"
    assert architect.goal
    assert "AI Product Builder" in " ".join(architect.memory)
    assert "not a cybersecurity scanner" in " ".join(architect.guardrails)
    assert "Product Intelligence" in " ".join(architect.workflow)
    assert "GitHub Export" in " ".join(architect.workflow)


def test_registry_lists_roles_deterministically_and_resolves_string_roles() -> None:
    registry = AgentRegistry.default()

    assert registry.roles() == [
        AgentRole.PRODUCT_MANAGER,
        AgentRole.UI_DESIGNER,
        AgentRole.UX_DESIGNER,
        AgentRole.VULS_ARCHITECT,
    ]
    assert registry.get("vuls_architect") == registry.get(AgentRole.VULS_ARCHITECT)


def test_registry_rejects_unknown_agent_role() -> None:
    registry = AgentRegistry.default()

    with pytest.raises(ValueError, match="Unknown agent role"):
        registry.get("qa_engineer")


def test_agent_memory_prompt_items_are_structured_for_future_orchestration() -> None:
    architect = AgentRegistry.default().get(AgentRole.VULS_ARCHITECT)

    items = agent_memory_prompt_items(architect)

    assert items[0] == "Agent: Vuls Architect (vuls_architect)."
    assert any(item.startswith("Goal:") for item in items)
    assert any(item.startswith("Memory:") for item in items)
    assert any(item.startswith("Does:") for item in items)
    assert any(item.startswith("Does not:") for item in items)
    assert any(item.startswith("Response format:") for item in items)
    assert any(item.startswith("Vuls rules:") for item in items)


def test_agent_workflow_planner_routes_dentistry_crm_to_product_ux_ui_sequence() -> None:
    workflow = plan_agent_workflow(
        AgentTask(user_prompt="Хочу CRM для стоматологии", platform="web")
    )

    assert isinstance(workflow, AgentWorkflow)
    assert [step.agent_role for step in workflow.steps] == [
        AgentRole.VULS_ARCHITECT,
        AgentRole.PRODUCT_MANAGER,
        AgentRole.UX_DESIGNER,
        AgentRole.UI_DESIGNER,
    ]
    assert workflow.agent_names() == [
        "Vuls Architect",
        "Product Manager",
        "UX Designer",
        "UI Designer",
    ]
    assert workflow.summary == (
        "Vuls Architect -> Product Manager -> UX Designer -> UI Designer"
    )


def test_agent_workflow_steps_are_structured_handoffs() -> None:
    workflow = plan_agent_workflow(
        AgentTask(user_prompt="Хочу CRM для стоматологии", platform="web")
    )

    assert all(isinstance(step, WorkflowStep) for step in workflow.steps)
    assert [step.order for step in workflow.steps] == [1, 2, 3, 4]
    assert workflow.steps[0].handoff_to == AgentRole.PRODUCT_MANAGER
    assert workflow.steps[1].handoff_to == AgentRole.UX_DESIGNER
    assert workflow.steps[2].handoff_to == AgentRole.UI_DESIGNER
    assert workflow.steps[3].handoff_to is None
    assert "Product Intelligence" in workflow.steps[1].expected_output
    assert "UX flow" in workflow.steps[2].expected_output
    assert "Design Intelligence" in workflow.steps[3].expected_output


def test_agent_workflow_prompt_items_are_deterministic() -> None:
    task = AgentTask(user_prompt="Хочу CRM для стоматологии", platform="web")

    first = plan_agent_workflow(task).prompt_items()
    second = plan_agent_workflow(task).prompt_items()

    assert first == second
    assert first[0] == (
        "Agent Workflow: Vuls Architect -> Product Manager -> UX Designer -> UI Designer."
    )
    assert any("Step 1: Vuls Architect" in item for item in first)
    assert any("Step 4: UI Designer" in item for item in first)


def test_execute_agent_workflow_runs_product_ux_and_ui_agents() -> None:
    context = _execution_context("I want a CRM for dentistry")
    workflow = plan_agent_workflow(
        AgentTask(user_prompt=context.user_prompt, domain="dentistry", platform="web")
    )

    results = execute_agent_workflow(workflow, context)

    assert [result.agent_role for result in results] == [
        AgentRole.VULS_ARCHITECT,
        AgentRole.PRODUCT_MANAGER,
        AgentRole.UX_DESIGNER,
        AgentRole.UI_DESIGNER,
    ]
    assert all(isinstance(result, AgentExecutionResult) for result in results)
    assert all(result.status == "completed" for result in results)

    product_result = _execution_result(results, AgentRole.PRODUCT_MANAGER)
    ux_result = _execution_result(results, AgentRole.UX_DESIGNER)
    ui_result = _execution_result(results, AgentRole.UI_DESIGNER)

    assert product_result.outputs["domain"] == "dentistry"
    assert "patient records" in product_result.outputs["mvp_scope"]
    assert "appointment scheduling" in product_result.outputs["must_have"]
    assert "clinic dashboard" in ux_result.outputs["screen_inventory"]
    assert "patient records" in ux_result.outputs["primary_journey"].lower()
    assert ui_result.outputs["visual_archetype"] == "clean_medical_dashboard"
    assert "clean medical dashboard" in ui_result.summary.lower()


def test_execute_agent_workflow_is_deterministic_and_uses_existing_contracts() -> None:
    context = _execution_context("I want a CRM for dentistry")
    workflow = plan_agent_workflow(
        AgentTask(user_prompt=context.user_prompt, domain="dentistry", platform="web")
    )

    first = execute_agent_workflow(workflow, context)
    second = execute_agent_workflow(workflow, context)

    assert [result.model_dump(mode="json") for result in first] == [
        result.model_dump(mode="json") for result in second
    ]

    product_result = _execution_result(first, AgentRole.PRODUCT_MANAGER)
    ux_result = _execution_result(first, AgentRole.UX_DESIGNER)
    ui_result = _execution_result(first, AgentRole.UI_DESIGNER)

    assert (
        product_result.outputs["must_have"]
        == context.product_intelligence.feature_prioritization.must_have
    )
    assert ux_result.outputs["ux_rules"] == context.design_contract.ux_rules
    assert (
        ui_result.outputs["open_design_prompt"]
        == context.design_contract.open_design_brief.prompt
    )


def test_agent_execution_result_prompt_items_are_structured() -> None:
    context = _execution_context("I want a CRM for dentistry")
    workflow = plan_agent_workflow(
        AgentTask(user_prompt=context.user_prompt, domain="dentistry", platform="web")
    )

    result = _execution_result(
        execute_agent_workflow(workflow, context),
        AgentRole.UI_DESIGNER,
    )

    prompt_items = result.prompt_items()

    assert prompt_items[0] == "Agent Execution: UI Designer (ui_designer) completed."
    assert any(item.startswith("Summary:") for item in prompt_items)
    assert any(item.startswith("Outputs:") for item in prompt_items)


def _execution_context(raw_idea: str) -> AgentExecutionContext:
    brief = ProjectBrief(
        title="Dental Clinic CRM",
        goal=raw_idea,
        target_users=["clinic owner", "front desk", "dentist"],
        must_have_features=["patients", "appointments", "treatment plans"],
        language_code="en",
    )
    product_intelligence = build_product_intelligence(
        raw_idea=raw_idea,
        brief=brief,
        selected_template_key="crm",
    )
    reference_analysis = analyze_references(
        ReferenceInput(
            domain=product_intelligence.product_memory.domain,
            user_intent=raw_idea,
            platform="web",
        )
    )
    design_contract = build_design_contract(
        DesignInput(
            product_brief=product_intelligence.product_brief,
            domain=product_intelligence.product_memory.domain,
            user_prompt=raw_idea,
            reference_analysis=reference_analysis,
            platform="web",
        )
    )
    return AgentExecutionContext(
        user_prompt=raw_idea,
        product_intelligence=product_intelligence,
        reference_analysis=reference_analysis,
        design_contract=design_contract,
    )


def _execution_result(
    results: list[AgentExecutionResult],
    role: AgentRole,
) -> AgentExecutionResult:
    return next(result for result in results if result.agent_role is role)
