from vuls.agent_intelligence import (
    AgentExecutionContext,
    AgentTask,
    critic_review_agent_outputs,
    execute_agent_workflow,
    plan_agent_workflow,
)
from vuls.design_intelligence import DesignInput, build_design_contract
from vuls.generation_contract import build_generation_contract
from vuls.llm.schemas import ProjectBrief
from vuls.product_intelligence import ProductIntelligence, build_product_intelligence
from vuls.reference_analysis import ReferenceInput, analyze_references
from vuls.reference_image_intelligence import (
    ReferenceImageInput,
    ReferenceImageItem,
    analyze_reference_images,
)
from vuls.reference_product_intelligence import (
    ReferenceProductAnalysis,
    ReferenceProductInput,
    analyze_reference_product,
)
from vuls.reference_ux_intelligence import (
    ReferenceUXAnalysis,
    ReferenceUXInput,
    analyze_reference_ux,
)


def test_generation_contract_builds_dental_crm_spec() -> None:
    context = _base_context(
        raw_idea="Create a CRM for a dentistry clinic",
        brief=ProjectBrief(
            title="Dentistry CRM",
            goal="Create a CRM for a dentistry clinic",
            target_users=["clinic manager", "front desk"],
            must_have_features=["patients", "appointments", "treatments", "billing"],
            language_code="en",
        ),
    )

    contract = build_generation_contract(
        product_intelligence=context.product_intelligence,
        design_contract=context.design_contract,
        agent_execution=context.agent_execution,
        agent_critic=context.agent_critic,
    )

    assert contract.application.name == "Dentistry CRM"
    assert contract.application.domain == "dentistry"
    assert contract.application.product_type == "CRM"
    assert [screen.name for screen in contract.screens] == [
        "Dashboard",
        "Patients",
        "Appointments",
        "Treatments",
        "Billing",
        "Settings",
    ]
    assert [entity.name for entity in contract.data_model.entities] == [
        "Patient",
        "Appointment",
        "Treatment",
        "Invoice",
    ]
    assert contract.navigation.pattern == "sidebar"
    assert contract.navigation.items == [
        "Dashboard",
        "Patients",
        "Appointments",
        "Treatments",
        "Billing",
        "Settings",
    ]
    assert _feature_names(contract) >= {
        "Create Patient",
        "Schedule Appointment",
        "Treatment History",
        "Invoice Management",
    }
    assert contract.agent_contract.passed is True


def test_generation_contract_keeps_user_domain_stronger_than_reference_product_type() -> None:
    context = _base_context(
        raw_idea="Create a CRM for a dentistry clinic inspired by this workspace UI",
        brief=ProjectBrief(
            title="Dentistry CRM",
            goal="Create a CRM for a dentistry clinic",
            target_users=["clinic manager", "front desk"],
            must_have_features=["patients", "appointments", "treatments", "billing"],
            language_code="en",
        ),
        reference_caption=(
            "Teamly SaaS workspace dashboard with sidebar navigation, documents, "
            "team members, billing, settings, search, and notifications."
        ),
        reference_tags=["saas", "workspace", "documents", "team", "billing", "settings"],
    )

    contract = build_generation_contract(
        product_intelligence=context.product_intelligence,
        reference_product_analysis=context.reference_product_analysis,
        reference_ux_analysis=context.reference_ux_analysis,
        design_contract=context.design_contract,
        agent_execution=context.agent_execution,
        agent_critic=context.agent_critic,
    )

    assert context.reference_product_analysis is not None
    assert context.reference_product_analysis.product_type == "SaaS Workspace"
    assert contract.application.domain == "dentistry"
    assert contract.application.product_type == "CRM"
    assert [screen.name for screen in contract.screens] == [
        "Dashboard",
        "Patients",
        "Appointments",
        "Treatments",
        "Billing",
        "Settings",
    ]


def test_generation_contract_accepts_failed_agent_critic_result() -> None:
    context = _base_context(
        raw_idea="Create a CRM for a dentistry clinic",
        brief=ProjectBrief(
            title="Dentistry CRM",
            goal="Create a CRM for a dentistry clinic",
            target_users=["clinic manager", "front desk"],
            must_have_features=["patients", "appointments", "treatments", "billing"],
            language_code="en",
        ),
    )
    failed_critic = context.agent_critic.model_copy(
        update={
            "passed": False,
            "score": 4,
            "summary": "Critic found issues, but the contract should still be inspectable.",
        }
    )

    contract = build_generation_contract(
        product_intelligence=context.product_intelligence,
        design_contract=context.design_contract,
        agent_execution=context.agent_execution,
        agent_critic=failed_critic,
    )

    assert contract.agent_contract.passed is False
    assert contract.agent_contract.score == 4
    assert [screen.name for screen in contract.screens]


def test_generation_contract_builds_saas_workspace_spec_from_references() -> None:
    context = _base_context(
        raw_idea="Build a Teamly-like workspace product",
        brief=ProjectBrief(
            title="Workspace Platform",
            goal="Build a Teamly-like workspace product",
            target_users=["team owner", "team member"],
            must_have_features=["workspace", "documents", "team members"],
            language_code="en",
        ),
        reference_caption=(
            "Teamly SaaS workspace dashboard with sidebar navigation, documents, "
            "team members, billing, settings, search, and notifications."
        ),
        reference_tags=["saas", "workspace", "documents", "team", "billing", "settings"],
    )

    contract = build_generation_contract(
        product_intelligence=context.product_intelligence,
        reference_product_analysis=context.reference_product_analysis,
        reference_ux_analysis=context.reference_ux_analysis,
        design_contract=context.design_contract,
        agent_execution=context.agent_execution,
        agent_critic=context.agent_critic,
    )

    assert contract.application.product_type == "SaaS Workspace"
    assert [screen.name for screen in contract.screens] == [
        "Workspace",
        "Dashboard",
        "Documents",
        "Team",
        "Billing",
        "Settings",
    ]
    assert [entity.name for entity in contract.data_model.entities] == [
        "Workspace",
        "Document",
        "Team Member",
        "Subscription",
        "Comment",
    ]
    assert contract.navigation.pattern == "sidebar"
    assert _feature_names(contract) >= {
        "Create Workspace",
        "Edit Document",
        "Invite Team Member",
        "Manage Billing",
    }


def test_generation_contract_builds_learning_app_spec_from_references() -> None:
    context = _base_context(
        raw_idea="Build a learning app for students",
        brief=ProjectBrief(
            title="Learning Platform",
            goal="Build a learning app for students",
            target_users=["student", "teacher"],
            must_have_features=["lessons", "quizzes", "progress"],
            language_code="en",
        ),
        reference_caption=(
            "Learning app screenshot with courses, lessons, quiz, student progress, "
            "achievements, profile, notifications, and onboarding."
        ),
        reference_tags=[
            "learning",
            "courses",
            "lessons",
            "quiz",
            "progress",
            "achievements",
        ],
    )

    contract = build_generation_contract(
        product_intelligence=context.product_intelligence,
        reference_product_analysis=context.reference_product_analysis,
        reference_ux_analysis=context.reference_ux_analysis,
        design_contract=context.design_contract,
        agent_execution=context.agent_execution,
        agent_critic=context.agent_critic,
    )

    assert contract.application.product_type == "Learning Platform"
    assert [screen.name for screen in contract.screens] == [
        "Lessons",
        "Progress",
        "Achievements",
        "Profile",
        "Settings",
    ]
    assert [entity.name for entity in contract.data_model.entities] == [
        "Learner",
        "Course",
        "Lesson",
        "Quiz Result",
        "Achievement",
    ]
    assert contract.navigation.pattern == "tab navigation"
    assert _feature_names(contract) >= {
        "Start Lesson",
        "Take Quiz",
        "Track Progress",
        "Earn Achievement",
    }


class GenerationContractContext:
    def __init__(
        self,
        *,
        product_intelligence: ProductIntelligence,
        design_contract: object,
        agent_execution: list[object],
        agent_critic: object,
        reference_product_analysis: ReferenceProductAnalysis | None,
        reference_ux_analysis: ReferenceUXAnalysis | None,
    ) -> None:
        self.product_intelligence = product_intelligence
        self.design_contract = design_contract
        self.agent_execution = agent_execution
        self.agent_critic = agent_critic
        self.reference_product_analysis = reference_product_analysis
        self.reference_ux_analysis = reference_ux_analysis


def _base_context(
    *,
    raw_idea: str,
    brief: ProjectBrief,
    reference_caption: str | None = None,
    reference_tags: list[str] | None = None,
) -> GenerationContractContext:
    product_intelligence = build_product_intelligence(
        raw_idea=raw_idea,
        brief=brief,
        selected_template_key="crm",
    )
    image_analysis = None
    if reference_caption is not None:
        image_analysis = analyze_reference_images(
            ReferenceImageInput(
                images=[
                    ReferenceImageItem(
                        filename="reference.png",
                        width=1440,
                        height=900,
                        caption=reference_caption,
                        tags=reference_tags or [],
                    )
                ],
                user_intent=raw_idea,
                platform="web",
            )
        )
    reference_analysis = analyze_references(
        ReferenceInput(
            domain=product_intelligence.product_memory.domain,
            user_intent=raw_idea,
            image_analysis=image_analysis,
            platform="web",
        )
    )
    reference_product_analysis = None
    reference_ux_analysis = None
    if image_analysis is not None:
        product_analysis = analyze_reference_product(
            ReferenceProductInput(
                reference_analysis=reference_analysis,
                image_analysis=image_analysis,
                user_intent=raw_idea,
                domain=product_intelligence.product_memory.domain,
                platform="web",
            )
        )
        reference_product_analysis = product_analysis
        reference_ux_analysis = analyze_reference_ux(
            ReferenceUXInput(
                reference_analysis=reference_analysis,
                reference_product_analysis=product_analysis,
                image_analysis=image_analysis,
                user_intent=raw_idea,
                domain=product_intelligence.product_memory.domain,
                platform="web",
            )
        )
    design_contract = build_design_contract(
        DesignInput(
            product_brief=product_intelligence.product_brief,
            domain=product_intelligence.product_memory.domain,
            user_prompt=raw_idea,
            references=[],
            reference_analysis=reference_analysis,
            platform="web",
        )
    )
    task = AgentTask(
        user_prompt=raw_idea,
        domain=product_intelligence.product_memory.domain,
        platform="web",
    )
    workflow = plan_agent_workflow(task)
    agent_execution = execute_agent_workflow(
        workflow,
        AgentExecutionContext(
            user_prompt=raw_idea,
            product_intelligence=product_intelligence,
            reference_analysis=reference_analysis,
            design_contract=design_contract,
            reference_image_analysis=image_analysis,
        ),
    )
    agent_critic = critic_review_agent_outputs(
        task=task,
        workflow=workflow,
        execution_results=agent_execution,
    )
    return GenerationContractContext(
        product_intelligence=product_intelligence,
        design_contract=design_contract,
        agent_execution=agent_execution,
        agent_critic=agent_critic,
        reference_product_analysis=reference_product_analysis,
        reference_ux_analysis=reference_ux_analysis,
    )


def _feature_names(contract: object) -> set[str]:
    return {feature.name for feature in contract.features}
