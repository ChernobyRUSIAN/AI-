from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from vuls.agent_intelligence import AgentCriticResult, AgentExecutionResult
from vuls.design_intelligence import DesignContract
from vuls.product_intelligence import ProductIntelligence
from vuls.reference_product_intelligence import ReferenceProductAnalysis
from vuls.reference_ux_intelligence import ReferenceUXAnalysis


class ApplicationSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    product_type: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    primary_goal: str = Field(min_length=1)


class ScreenSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    route: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    primary_actions: list[str] = Field(default_factory=list)


class NavigationSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    pattern: str = Field(min_length=1)
    items: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)


class EntitySpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    plural_name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    fields: list[str] = Field(min_length=1)


class FeatureSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    screen: str = Field(min_length=1)
    entity: str | None = None
    description: str = Field(min_length=1)


class DataModelSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    entities: list[EntitySpec] = Field(min_length=1)
    relationships: list[str] = Field(default_factory=list)


class GenerationContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    application: ApplicationSpec
    screens: list[ScreenSpec] = Field(min_length=1)
    navigation: NavigationSpec
    features: list[FeatureSpec] = Field(min_length=1)
    data_model: DataModelSpec
    design_constraints: list[str] = Field(default_factory=list)
    agent_outputs: list[str] = Field(default_factory=list)
    agent_contract: AgentCriticResult


@dataclass(frozen=True)
class ContractProfile:
    key: str
    product_type: str
    screens: tuple[tuple[str, str, tuple[str, ...]], ...]
    entities: tuple[tuple[str, str, str, tuple[str, ...]], ...]
    features: tuple[tuple[str, str, str | None, str], ...]
    navigation_pattern: str
    navigation_rationale: str
    relationships: tuple[str, ...]


DENTAL_CRM_PROFILE = ContractProfile(
    key="dental_crm",
    product_type="CRM",
    screens=(
        ("Dashboard", "Daily clinic overview, risks, and next actions.", ("Review KPIs",)),
        ("Patients", "Patient records, contact details, and clinical status.", ("Create Patient",)),
        (
            "Appointments",
            "Schedule, update, and track clinic appointments.",
            ("Schedule Appointment",),
        ),
        (
            "Treatments",
            "Treatment plans, history, and follow-up work.",
            ("Update Treatment",),
        ),
        ("Billing", "Invoices, payment status, and clinic billing tasks.", ("Create Invoice",)),
        ("Settings", "Clinic team, roles, preferences, and configuration.", ("Manage Settings",)),
    ),
    entities=(
        (
            "Patient",
            "Patients",
            "Person receiving care at the dental clinic.",
            ("id", "name", "phone", "email", "status", "last_visit"),
        ),
        (
            "Appointment",
            "Appointments",
            "Scheduled clinic visit for a patient.",
            ("id", "patient_id", "doctor", "scheduled_at", "status", "notes"),
        ),
        (
            "Treatment",
            "Treatments",
            "Treatment plan or clinical procedure linked to a patient.",
            ("id", "patient_id", "appointment_id", "name", "status", "cost"),
        ),
        (
            "Invoice",
            "Invoices",
            "Billing record for appointments and treatments.",
            ("id", "patient_id", "treatment_id", "amount", "status", "due_date"),
        ),
    ),
    features=(
        ("Create Patient", "Patients", "Patient", "Add and edit patient records."),
        (
            "Schedule Appointment",
            "Appointments",
            "Appointment",
            "Book visits and update appointment status.",
        ),
        (
            "Treatment History",
            "Treatments",
            "Treatment",
            "Track treatment plans and completed procedures.",
        ),
        (
            "Invoice Management",
            "Billing",
            "Invoice",
            "Create invoices and track payment status.",
        ),
    ),
    navigation_pattern="sidebar",
    navigation_rationale="Dental CRM users need persistent access to clinic operations.",
    relationships=(
        "Patient has many Appointments.",
        "Patient has many Treatments.",
        "Treatment can create one Invoice.",
    ),
)


GENERIC_CRM_PROFILE = ContractProfile(
    key="generic_crm",
    product_type="CRM",
    screens=(
        ("Dashboard", "Operational overview and next actions.", ("Review KPIs",)),
        ("Customers", "Customer records and activity.", ("Create Customer",)),
        ("Deals", "Pipeline and revenue opportunities.", ("Update Deal",)),
        ("Reports", "Performance reporting.", ("Review Reports",)),
        ("Settings", "Team and workflow configuration.", ("Manage Settings",)),
    ),
    entities=(
        (
            "Customer",
            "Customers",
            "Customer or account record.",
            ("id", "name", "email", "phone", "segment", "status"),
        ),
        (
            "Deal",
            "Deals",
            "Revenue opportunity linked to a customer.",
            ("id", "customer_id", "title", "stage", "value", "owner"),
        ),
        (
            "Task",
            "Tasks",
            "Follow-up or operational task.",
            ("id", "customer_id", "title", "owner", "status", "due_date"),
        ),
    ),
    features=(
        ("Create Customer", "Customers", "Customer", "Add and edit customer records."),
        ("Manage Deals", "Deals", "Deal", "Move deals through pipeline stages."),
        ("Track Results", "Reports", None, "Review CRM performance and activity."),
    ),
    navigation_pattern="sidebar",
    navigation_rationale="CRM work benefits from persistent sidebar navigation.",
    relationships=("Customer has many Deals.", "Customer has many Tasks."),
)


SAAS_WORKSPACE_PROFILE = ContractProfile(
    key="saas_workspace",
    product_type="SaaS Workspace",
    screens=(
        ("Workspace", "Current workspace context and activity.", ("Create Workspace",)),
        ("Dashboard", "Workspace overview and shortcuts.", ("Review Activity",)),
        ("Documents", "Shared documents and knowledge base.", ("Edit Document",)),
        ("Team", "Members, roles, and collaboration state.", ("Invite Team Member",)),
        ("Billing", "Plan, usage, and invoices.", ("Manage Billing",)),
        ("Settings", "Workspace configuration.", ("Manage Settings",)),
    ),
    entities=(
        (
            "Workspace",
            "Workspaces",
            "Team container for documents, members, and settings.",
            ("id", "name", "owner_id", "plan", "created_at"),
        ),
        (
            "Document",
            "Documents",
            "Shared knowledge item inside a workspace.",
            ("id", "workspace_id", "title", "content", "status", "updated_at"),
        ),
        (
            "Team Member",
            "Team Members",
            "User collaborating in a workspace.",
            ("id", "workspace_id", "name", "email", "role", "status"),
        ),
        (
            "Subscription",
            "Subscriptions",
            "Billing plan and subscription state.",
            ("id", "workspace_id", "plan", "status", "renewal_date"),
        ),
        (
            "Comment",
            "Comments",
            "Conversation on a document or workspace item.",
            ("id", "document_id", "author_id", "body", "created_at"),
        ),
    ),
    features=(
        ("Create Workspace", "Workspace", "Workspace", "Create and switch workspaces."),
        ("Edit Document", "Documents", "Document", "Create and update shared documents."),
        (
            "Invite Team Member",
            "Team",
            "Team Member",
            "Invite collaborators and manage roles.",
        ),
        ("Manage Billing", "Billing", "Subscription", "Review plan and billing status."),
    ),
    navigation_pattern="sidebar",
    navigation_rationale="Workspace products need persistent access to product areas.",
    relationships=(
        "Workspace has many Documents.",
        "Workspace has many Team Members.",
        "Document has many Comments.",
        "Workspace has one Subscription.",
    ),
)


LEARNING_PLATFORM_PROFILE = ContractProfile(
    key="learning_platform",
    product_type="Learning Platform",
    screens=(
        ("Lessons", "Browse and continue learning content.", ("Start Lesson",)),
        ("Progress", "Completion, streak, and learning analytics.", ("Track Progress",)),
        ("Achievements", "Milestones and reward states.", ("Earn Achievement",)),
        ("Profile", "Learner identity, goals, and preferences.", ("Update Profile",)),
        ("Settings", "Notifications and app preferences.", ("Manage Settings",)),
    ),
    entities=(
        (
            "Learner",
            "Learners",
            "Person using the learning platform.",
            ("id", "name", "email", "level", "streak"),
        ),
        (
            "Course",
            "Courses",
            "Learning track containing lessons.",
            ("id", "title", "description", "difficulty", "status"),
        ),
        (
            "Lesson",
            "Lessons",
            "Individual learning unit.",
            ("id", "course_id", "title", "content", "duration_minutes"),
        ),
        (
            "Quiz Result",
            "Quiz Results",
            "Score and feedback for a lesson quiz.",
            ("id", "learner_id", "lesson_id", "score", "completed_at"),
        ),
        (
            "Achievement",
            "Achievements",
            "Reward earned by a learner.",
            ("id", "learner_id", "name", "earned_at", "badge"),
        ),
    ),
    features=(
        ("Start Lesson", "Lessons", "Lesson", "Resume or start lesson content."),
        ("Take Quiz", "Lessons", "Quiz Result", "Submit answers and receive feedback."),
        ("Track Progress", "Progress", "Learner", "Show progress, streak, and completion."),
        (
            "Earn Achievement",
            "Achievements",
            "Achievement",
            "Award milestones that encourage return sessions.",
        ),
    ),
    navigation_pattern="tab navigation",
    navigation_rationale="Learning apps benefit from fast access to content and progress.",
    relationships=(
        "Course has many Lessons.",
        "Learner has many Quiz Results.",
        "Learner has many Achievements.",
    ),
)


def build_generation_contract(
    *,
    product_intelligence: ProductIntelligence,
    design_contract: DesignContract,
    agent_execution: list[AgentExecutionResult],
    agent_critic: AgentCriticResult,
    reference_product_analysis: ReferenceProductAnalysis | None = None,
    reference_ux_analysis: ReferenceUXAnalysis | None = None,
) -> GenerationContract:
    profile = _select_contract_profile(
        product_intelligence=product_intelligence,
        reference_product_analysis=reference_product_analysis,
    )
    compatible_reference_ux = _compatible_reference_ux(profile, reference_ux_analysis)
    screens = _screen_specs(profile, compatible_reference_ux)
    navigation = _navigation_spec(profile, screens, compatible_reference_ux)
    return GenerationContract(
        application=ApplicationSpec(
            name=product_intelligence.product_brief.product_name,
            product_type=profile.product_type,
            domain=product_intelligence.product_memory.domain,
            platform=design_contract.platform,
            primary_goal=_primary_goal(product_intelligence, compatible_reference_ux),
        ),
        screens=screens,
        navigation=navigation,
        features=_feature_specs(profile),
        data_model=DataModelSpec(
            entities=_entity_specs(profile),
            relationships=list(profile.relationships),
        ),
        design_constraints=_design_constraints(design_contract),
        agent_outputs=_agent_output_summaries(agent_execution),
        agent_contract=agent_critic,
    )


def _select_contract_profile(
    *,
    product_intelligence: ProductIntelligence,
    reference_product_analysis: ReferenceProductAnalysis | None,
) -> ContractProfile:
    if product_intelligence.product_memory.domain == "dentistry":
        return DENTAL_CRM_PROFILE
    if (
        reference_product_analysis is not None
        and reference_product_analysis.product_type == "SaaS Workspace"
    ):
        return SAAS_WORKSPACE_PROFILE
    if (
        reference_product_analysis is not None
        and reference_product_analysis.product_type == "Learning Platform"
    ):
        return LEARNING_PLATFORM_PROFILE
    if (
        reference_product_analysis is not None
        and reference_product_analysis.product_type == "CRM"
    ):
        return GENERIC_CRM_PROFILE
    if _contains_crm_signal(product_intelligence):
        return GENERIC_CRM_PROFILE
    return GENERIC_CRM_PROFILE


def _compatible_reference_ux(
    profile: ContractProfile,
    reference_ux_analysis: ReferenceUXAnalysis | None,
) -> ReferenceUXAnalysis | None:
    if reference_ux_analysis is None or not reference_ux_analysis.core_screens:
        return reference_ux_analysis
    profile_screen_names = {name for name, _purpose, _actions in profile.screens}
    reference_screen_names = {screen.name for screen in reference_ux_analysis.core_screens}
    overlap = len(profile_screen_names & reference_screen_names)
    minimum_overlap = max(2, len(reference_screen_names) // 2 + 1)
    return reference_ux_analysis if overlap >= minimum_overlap else None


def _screen_specs(
    profile: ContractProfile,
    reference_ux_analysis: ReferenceUXAnalysis | None,
) -> list[ScreenSpec]:
    profile_screens = {name: (purpose, actions) for name, purpose, actions in profile.screens}
    if reference_ux_analysis is not None and reference_ux_analysis.core_screens:
        screens: list[ScreenSpec] = []
        for core_screen in reference_ux_analysis.core_screens:
            purpose, actions = profile_screens.get(
                core_screen.name,
                (core_screen.purpose, (f"Open {core_screen.name}",)),
            )
            screens.append(
                ScreenSpec(
                    name=core_screen.name,
                    route=_route_for(core_screen.name),
                    purpose=purpose,
                    primary_actions=list(actions),
                )
            )
        return screens

    return [
        ScreenSpec(
            name=name,
            route=_route_for(name),
            purpose=purpose,
            primary_actions=list(actions),
        )
        for name, purpose, actions in profile.screens
    ]


def _navigation_spec(
    profile: ContractProfile,
    screens: list[ScreenSpec],
    reference_ux_analysis: ReferenceUXAnalysis | None,
) -> NavigationSpec:
    pattern = profile.navigation_pattern
    rationale = profile.navigation_rationale
    if reference_ux_analysis is not None:
        reference_patterns = {item.pattern for item in reference_ux_analysis.navigation_patterns}
        if "sidebar-first" in reference_patterns:
            pattern = "sidebar"
            rationale = "Reference UX signals prefer persistent sidebar navigation."
        elif "tab navigation" in reference_patterns or "content-first" in reference_patterns:
            pattern = profile.navigation_pattern
            rationale = "Reference UX signals emphasize fast access to core content."
    return NavigationSpec(
        pattern=pattern,
        items=[screen.name for screen in screens],
        rationale=rationale,
    )


def _entity_specs(profile: ContractProfile) -> list[EntitySpec]:
    return [
        EntitySpec(
            name=name,
            plural_name=plural_name,
            purpose=purpose,
            fields=list(fields),
        )
        for name, plural_name, purpose, fields in profile.entities
    ]


def _feature_specs(profile: ContractProfile) -> list[FeatureSpec]:
    return [
        FeatureSpec(
            name=name,
            screen=screen,
            entity=entity,
            description=description,
        )
        for name, screen, entity, description in profile.features
    ]


def _primary_goal(
    product_intelligence: ProductIntelligence,
    reference_ux_analysis: ReferenceUXAnalysis | None,
) -> str:
    if reference_ux_analysis is not None and reference_ux_analysis.primary_goal != "Unknown":
        return reference_ux_analysis.primary_goal
    return product_intelligence.product_brief.value_proposition


def _design_constraints(design_contract: DesignContract) -> list[str]:
    return [
        f"archetype={design_contract.visual_archetype.key}",
        f"composition={design_contract.screen_composition}",
        f"components={'; '.join(design_contract.component_rules.primary_components)}",
        f"ux={'; '.join(design_contract.ux_rules)}",
    ]


def _agent_output_summaries(agent_execution: list[AgentExecutionResult]) -> list[str]:
    return [
        f"{result.agent_name}: {result.summary}"
        for result in agent_execution
        if result.status == "completed"
    ]


def _contains_crm_signal(product_intelligence: ProductIntelligence) -> bool:
    text = " ".join(
        [
            product_intelligence.product_brief.product_name,
            product_intelligence.product_memory.source_idea,
            product_intelligence.product_memory.selected_template or "",
        ]
    ).casefold()
    return "crm" in text


def _route_for(screen_name: str) -> str:
    route = re.sub(r"[^a-z0-9]+", "-", screen_name.casefold()).strip("-")
    return "/" + (route or "dashboard")
