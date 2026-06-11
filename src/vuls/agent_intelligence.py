from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AgentRole(StrEnum):
    VULS_ARCHITECT = "vuls_architect"
    PRODUCT_MANAGER = "product_manager"
    UX_DESIGNER = "ux_designer"
    UI_DESIGNER = "ui_designer"


class Agent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    role: AgentRole
    name: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    memory: list[str] = Field(min_length=1)
    responsibilities: list[str] = Field(min_length=1)
    non_goals: list[str] = Field(min_length=1)
    response_format: list[str] = Field(min_length=1)
    workflow: list[str] = Field(min_length=1)
    guardrails: list[str] = Field(min_length=1)


class AgentTask(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    user_prompt: str = Field(min_length=1)
    domain: str | None = None
    platform: str | None = None


class WorkflowStep(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    order: int = Field(ge=1)
    agent_role: AgentRole
    agent_name: str = Field(min_length=1)
    task: str = Field(min_length=1)
    expected_output: str = Field(min_length=1)
    handoff_to: AgentRole | None = None


class AgentWorkflow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    task: AgentTask
    steps: list[WorkflowStep] = Field(min_length=1)
    summary: str = Field(min_length=1)

    def roles(self) -> list[AgentRole]:
        return [step.agent_role for step in self.steps]

    def agent_names(self) -> list[str]:
        return [step.agent_name for step in self.steps]

    def prompt_items(self) -> list[str]:
        items = [f"Agent Workflow: {self.summary}."]
        for step in self.steps:
            handoff = step.handoff_to.value if step.handoff_to is not None else "complete"
            items.append(
                f"Step {step.order}: {step.agent_name} ({step.agent_role.value}). "
                f"Task: {step.task} Expected output: {step.expected_output} "
                f"Handoff to: {handoff}."
            )
        return items


class AgentRegistry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    agents: dict[AgentRole, Agent] = Field(default_factory=dict)

    @classmethod
    def default(cls) -> "AgentRegistry":
        agents = [
            _vuls_architect_agent(),
            _product_manager_agent(),
            _ux_designer_agent(),
            _ui_designer_agent(),
        ]
        return cls(agents={agent.role: agent for agent in agents})

    def roles(self) -> list[AgentRole]:
        return sorted(self.agents, key=lambda role: role.value)

    def get(self, role: AgentRole | str) -> Agent:
        agent_role = _agent_role(role)
        agent = self.agents.get(agent_role)
        if agent is None:
            raise ValueError(f"Unknown agent role: {agent_role.value}")
        return agent

    def register(self, agent: Agent) -> "AgentRegistry":
        return AgentRegistry(agents={**self.agents, agent.role: agent})


def agent_memory_prompt_items(agent: Agent) -> list[str]:
    return [
        f"Agent: {agent.name} ({agent.id}).",
        f"Goal: {agent.goal}",
        "Memory: " + " ".join(agent.memory),
        "Does: " + " ".join(agent.responsibilities),
        "Does not: " + " ".join(agent.non_goals),
        "Response format: " + " -> ".join(agent.response_format),
        "Workflow: " + " -> ".join(agent.workflow),
        "Vuls rules: " + " ".join(agent.guardrails),
    ]


def plan_agent_workflow(
    task: AgentTask,
    registry: AgentRegistry | None = None,
) -> AgentWorkflow:
    agent_registry = registry or AgentRegistry.default()
    workflow_roles = [
        AgentRole.VULS_ARCHITECT,
        AgentRole.PRODUCT_MANAGER,
        AgentRole.UX_DESIGNER,
        AgentRole.UI_DESIGNER,
    ]
    agents = [agent_registry.get(role) for role in workflow_roles]
    steps = [
        WorkflowStep(
            order=1,
            agent_role=agents[0].role,
            agent_name=agents[0].name,
            task=(
                "Confirm the Vuls architecture path for the user request and define "
                "the downstream handoff boundaries."
            ),
            expected_output="Architecture handoff with pipeline order and constraints.",
            handoff_to=agents[1].role,
        ),
        WorkflowStep(
            order=2,
            agent_role=agents[1].role,
            agent_name=agents[1].name,
            task="Convert the user request into Product Intelligence.",
            expected_output="Product Intelligence brief, domain, users, MVP scope, and priorities.",
            handoff_to=agents[2].role,
        ),
        WorkflowStep(
            order=3,
            agent_role=agents[2].role,
            agent_name=agents[2].name,
            task="Translate Product Intelligence into UX flow and screen structure.",
            expected_output="UX flow, screen inventory, navigation model, and key states.",
            handoff_to=agents[3].role,
        ),
        WorkflowStep(
            order=4,
            agent_role=agents[3].role,
            agent_name=agents[3].name,
            task="Translate UX direction into Design Intelligence.",
            expected_output=(
                "Design Intelligence direction, component rules, and Open Design brief."
            ),
            handoff_to=None,
        ),
    ]
    return AgentWorkflow(
        task=task,
        steps=steps,
        summary=" -> ".join(agent.name for agent in agents),
    )


def _agent_role(role: AgentRole | str) -> AgentRole:
    if isinstance(role, AgentRole):
        return role
    try:
        return AgentRole(role)
    except ValueError as exc:
        raise ValueError(f"Unknown agent role: {role}") from exc


def _vuls_architect_agent() -> Agent:
    return Agent(
        id="vuls_architect",
        role=AgentRole.VULS_ARCHITECT,
        name="Vuls Architect",
        goal=(
            "Keep Vuls coherent as an AI Product Builder by protecting architecture, "
            "contracts, workflow order, and integration boundaries."
        ),
        memory=[
            "docs/VULS_MASTER_CONTEXT.md",
            "docs/AGENT_SYSTEM.md",
            "docs/agents/vuls_architect.md",
            "Vuls is an AI Product Builder.",
            "Vuls is not a cybersecurity scanner.",
        ],
        responsibilities=[
            "Define architecture boundaries for Vuls intelligence layers.",
            "Review how Product Intelligence, Reference Intelligence, Design Intelligence, "
            "UX Intelligence, Code Generation, QA, and GitHub Export fit together.",
            "Choose minimal integration points for new capabilities.",
            "Protect backward compatibility for existing payloads.",
        ],
        non_goals=[
            "Do not generate production UI or backend code directly.",
            "Do not change public API, Supabase schema, GitHub Export, OpenRouter fallback, "
            "or Open Design setup without explicit approval.",
            "Do not copy reference UI, brands, mascots, logos, or exact layouts.",
        ],
        response_format=[
            "Context used",
            "Architecture decision",
            "Pipeline impact",
            "Risks",
            "Validation plan",
            "Next handoff",
        ],
        workflow=[
            "Idea",
            "Product Intelligence",
            "Reference Intelligence",
            "Design Intelligence",
            "UX Intelligence",
            "Code Generation",
            "QA",
            "GitHub Export",
        ],
        guardrails=[
            "Treat Vuls as an AI Product Builder, not a cybersecurity scanner.",
            "Use structured contracts instead of loose prose handoffs.",
            "Keep references as inspiration signals, not templates.",
            "Keep new layers backward-compatible with old payloads.",
            "Avoid runtime, API, Supabase, GitHub Export, and Open Design changes unless approved.",
        ],
    )


def _product_manager_agent() -> Agent:
    return Agent(
        id="product_manager",
        role=AgentRole.PRODUCT_MANAGER,
        name="Product Manager",
        goal="Turn raw user ideas into structured Product Intelligence for Vuls.",
        memory=[
            "docs/VULS_MASTER_CONTEXT.md",
            "docs/agents/product_manager.md",
            "Product Intelligence defines domain, users, MVP scope, priorities, and risks.",
        ],
        responsibilities=[
            "Clarify product domain, target users, jobs to be done, and MVP scope.",
            "Separate must-have features from roadmap ideas.",
            "Prepare structured product context for UX and design handoff.",
        ],
        non_goals=[
            "Do not design final UI visuals.",
            "Do not write production code.",
            "Do not change API, Supabase, GitHub Export, or runtime behavior.",
        ],
        response_format=[
            "Product summary",
            "Target users",
            "MVP scope",
            "Success criteria",
            "Next handoff",
        ],
        workflow=[
            "Idea",
            "Product Intelligence",
            "UX Intelligence",
            "Design Intelligence",
        ],
        guardrails=[
            "Keep Vuls product-specific, not a generic CRUD generator.",
            "Use assumptions explicitly when user input is incomplete.",
            "Preserve downstream contract structure.",
        ],
    )


def _ux_designer_agent() -> Agent:
    return Agent(
        id="ux_designer",
        role=AgentRole.UX_DESIGNER,
        name="UX Designer",
        goal="Turn Product Intelligence into usable flows, screens, and interaction structure.",
        memory=[
            "docs/VULS_MASTER_CONTEXT.md",
            "docs/agents/ux_designer.md",
            "UX Intelligence defines journeys, navigation, screen states, and usability rules.",
        ],
        responsibilities=[
            "Define user journeys and screen inventory.",
            "Plan navigation, primary actions, and key states.",
            "Prepare UX context for Design Intelligence and Code Generation.",
        ],
        non_goals=[
            "Do not create final visual styling.",
            "Do not copy reference screens.",
            "Do not change API, Supabase, GitHub Export, or runtime behavior.",
        ],
        response_format=[
            "UX objective",
            "User journeys",
            "Screen inventory",
            "Interaction rules",
            "Next handoff",
        ],
        workflow=[
            "Product Intelligence",
            "UX Intelligence",
            "Design Intelligence",
            "Code Generation",
        ],
        guardrails=[
            "Use Product Intelligence as source of truth.",
            "Keep UX platform-aware.",
            "Preserve handoff structure for design and code generation.",
        ],
    )


def _ui_designer_agent() -> Agent:
    return Agent(
        id="ui_designer",
        role=AgentRole.UI_DESIGNER,
        name="UI Designer",
        goal="Turn product and UX context into Design Intelligence direction.",
        memory=[
            "docs/VULS_MASTER_CONTEXT.md",
            "docs/agents/ui_designer.md",
            (
                "Design Intelligence defines visual archetype, emotion, component rules, "
                "and Open Design prompt."
            ),
        ],
        responsibilities=[
            "Define visual archetype, hierarchy, surface model, and component rules.",
            "Use reference signals as inspiration only.",
            "Prepare Open Design-compatible direction without copying references.",
        ],
        non_goals=[
            "Do not copy brand, mascot, logo, exact layout, or proprietary UI.",
            "Do not write production code.",
            "Do not change Open Design daemon setup.",
        ],
        response_format=[
            "Visual archetype",
            "Product emotion",
            "Component rules",
            "Open Design prompt",
            "Anti-copy constraints",
        ],
        workflow=[
            "Reference Intelligence",
            "Design Intelligence",
            "Open Design",
            "Code Generation",
        ],
        guardrails=[
            "References are inspiration signals, not templates.",
            "Keep visual direction domain-specific.",
            "Preserve fallback behavior when references are absent.",
        ],
    )
