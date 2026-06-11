import pytest

from vuls.agent_intelligence import (
    AgentRegistry,
    AgentRole,
    AgentTask,
    AgentWorkflow,
    WorkflowStep,
    agent_memory_prompt_items,
    plan_agent_workflow,
)


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
