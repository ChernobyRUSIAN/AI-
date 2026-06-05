import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from vuls.llm.schemas import ProjectBrief


class ProductBriefDocument(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    product_name: str = Field(min_length=1)
    target_audience: list[str] = Field(min_length=1)
    user_problems: list[str] = Field(min_length=1)
    value_proposition: str = Field(min_length=1)
    core_features: list[str] = Field(min_length=1)
    mvp_scope: list[str] = Field(min_length=1)
    monetization: list[str] = Field(min_length=1)
    risks: list[str] = Field(min_length=1)
    success_metrics: list[str] = Field(min_length=1)


class FeaturePrioritization(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    must_have: list[str] = Field(min_length=1)
    should_have: list[str] = Field(min_length=1)
    could_have: list[str] = Field(min_length=1)
    future: list[str] = Field(min_length=1)


class RoadmapPhase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    goals: list[str] = Field(min_length=1)
    features: list[str] = Field(min_length=1)
    metrics: list[str] = Field(min_length=1)


class ProjectRoadmap(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    phases: list[RoadmapPhase] = Field(min_length=3, max_length=3)


class ProductMemoryDocument(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_idea: str = Field(min_length=1)
    product_brief: ProductBriefDocument
    generator_decisions: list[str] = Field(min_length=1)
    selected_template: str | None
    domain: str = Field(min_length=1)
    change_history: list[str] = Field(min_length=1)
    feature_prioritization: FeaturePrioritization
    roadmap: ProjectRoadmap


class ProductIntelligence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    product_brief: ProductBriefDocument
    feature_prioritization: FeaturePrioritization
    roadmap: ProjectRoadmap
    product_memory: ProductMemoryDocument

    def to_project_brief_payload(self) -> dict[str, Any]:
        return {
            "product_brief": self.product_brief.model_dump(mode="json"),
            "feature_prioritization": self.feature_prioritization.model_dump(mode="json"),
            "roadmap": self.roadmap.model_dump(mode="json"),
            "product_memory": self.product_memory.model_dump(mode="json"),
        }


@dataclass(frozen=True)
class ProductDomainProfile:
    key: str
    keywords: tuple[str, ...]
    target_audience: tuple[str, ...]
    problems: tuple[str, ...]
    must_have: tuple[str, ...]
    should_have: tuple[str, ...]
    could_have: tuple[str, ...]
    future: tuple[str, ...]
    monetization: tuple[str, ...]
    risks: tuple[str, ...]
    metrics: tuple[str, ...]


DOMAIN_PROFILES: dict[str, ProductDomainProfile] = {
    "dentistry": ProductDomainProfile(
        key="dentistry",
        keywords=(
            "dentistry",
            "dental",
            "dentist",
            "clinic",
            "patients",
            "appointments",
            "treatments",
            "stomatology",
        ),
        target_audience=("clinic owners", "front-desk teams", "dentists"),
        problems=(
            "Patient records are scattered across tools.",
            "Appointments and treatment status are hard to track in one workflow.",
            "Clinic teams need a fast way to coordinate daily operations.",
        ),
        must_have=("patient records", "appointment scheduling", "treatment tracking"),
        should_have=("doctor schedules", "visit history", "treatment notes"),
        could_have=("automated reminders", "basic billing exports", "intake forms"),
        future=("AI visit summaries", "advanced clinic analytics", "insurance workflows"),
        monetization=("per-clinic subscription", "per-seat staff plan", "premium analytics add-on"),
        risks=(
            "Healthcare data needs careful access control.",
            "Clinic workflows may vary by country and specialty.",
        ),
        metrics=("active clinic users", "appointments tracked", "patient record completion rate"),
    ),
    "fitness": ProductDomainProfile(
        key="fitness",
        keywords=(
            "fitness",
            "gym",
            "trainer",
            "trainers",
            "workout",
            "workouts",
            "member",
            "members",
            "membership",
            "memberships",
        ),
        target_audience=("gym members", "trainers", "fitness studio owners"),
        problems=(
            "Members need clear workout guidance between coaching sessions.",
            "Trainers need visibility into progress and adherence.",
            "Fitness businesses need a simple way to retain members.",
        ),
        must_have=("member profiles", "workout plans", "progress tracking"),
        should_have=("trainer assignments", "class planning", "membership status"),
        could_have=("nutrition notes", "habit reminders", "wearable data import"),
        future=("AI coaching assistant", "adaptive training plans", "payment automation"),
        monetization=("monthly member subscription", "studio plan", "coach workspace add-on"),
        risks=(
            "Health recommendations must avoid unsafe medical claims.",
            "Engagement can drop if plans are not personalized.",
        ),
        metrics=("weekly active members", "completed workouts", "member retention"),
    ),
    "beauty_salon": ProductDomainProfile(
        key="beauty_salon",
        keywords=("beauty", "salon", "spa", "masters", "services", "bookings", "stylist"),
        target_audience=("salon owners", "masters", "reception teams"),
        problems=(
            "Bookings, client notes and service history are often disconnected.",
            "Salon teams need a reliable daily schedule view.",
            "Managers need visibility into revenue-driving services.",
        ),
        must_have=("client profiles", "service catalog", "booking management"),
        should_have=("master schedules", "service history", "daily calendar"),
        could_have=("reminders", "loyalty notes", "retail product tracking"),
        future=("online booking", "payment integrations", "demand forecasting"),
        monetization=("monthly salon subscription", "per-master plan", "booking add-on"),
        risks=(
            "No-show handling needs strong notification workflows.",
            "Service catalogs can become complex for larger salons.",
        ),
        metrics=("bookings created", "repeat clients", "master utilization"),
    ),
    "auto_service": ProductDomainProfile(
        key="auto_service",
        keywords=(
            "auto service",
            "car service",
            "repair",
            "repairs",
            "mechanic",
            "mechanics",
            "work order",
            "work orders",
            "vehicles",
        ),
        target_audience=("auto service owners", "mechanics", "service advisors"),
        problems=(
            "Repair requests and work orders need clear ownership.",
            "Service teams need one place for vehicle history and repair status.",
            "Owners need operational visibility without spreadsheet work.",
        ),
        must_have=("vehicle records", "repair orders", "mechanic assignments"),
        should_have=("work order status", "parts notes", "service history"),
        could_have=("customer notifications", "estimate approvals", "inventory tracking"),
        future=("diagnostic integrations", "supplier integrations", "fleet account support"),
        monetization=("shop subscription", "per-location plan", "advanced reporting add-on"),
        risks=(
            "Repair workflow details vary by shop size.",
            "Parts and estimate workflows can expand scope quickly.",
        ),
        metrics=("work orders completed", "average repair cycle time", "mechanic utilization"),
    ),
    "task_saas": ProductDomainProfile(
        key="task_saas",
        keywords=(
            "task",
            "tasks",
            "project management",
            "productivity",
            "kanban",
            "collaboration",
            "todo",
            "saas",
        ),
        target_audience=("team leads", "operators", "small business teams"),
        problems=(
            "Teams lose context when tasks, owners and deadlines live in separate places.",
            "Managers need a simple view of progress and blockers.",
            "Operators need fast daily execution without heavy setup.",
        ),
        must_have=("task management", "project workspaces", "collaboration"),
        should_have=("status boards", "assignment tracking", "deadline reminders"),
        could_have=("templates", "activity feed", "basic reporting"),
        future=("automation rules", "AI planning assistant", "third-party integrations"),
        monetization=("freemium plan", "per-seat subscription", "team workspace upgrades"),
        risks=(
            "Task management is a crowded category.",
            "The product must stay lightweight to differentiate.",
        ),
        metrics=("active teams", "tasks completed", "weekly retained users"),
    ),
    "generic": ProductDomainProfile(
        key="generic",
        keywords=(),
        target_audience=("business owners", "operators", "team members"),
        problems=(
            "Core operations are fragmented across manual tools.",
            "Teams need a faster way to track customers, work and outcomes.",
            "Decision makers lack a simple product view of progress.",
        ),
        must_have=("dashboard", "record management", "status tracking"),
        should_have=("role-based workflows", "activity history", "simple reporting"),
        could_have=("notifications", "imports", "export tools"),
        future=("AI assistant", "advanced analytics", "workflow automation"),
        monetization=("monthly subscription", "per-seat pricing", "premium automation plan"),
        risks=(
            "The MVP must avoid overbuilding before user validation.",
            "The workflow needs enough domain detail to feel useful.",
        ),
        metrics=("active users", "records created", "weekly retention"),
    ),
}


def build_product_intelligence(
    *,
    raw_idea: str,
    brief: ProjectBrief,
    selected_template_key: str | None,
) -> ProductIntelligence:
    domain = detect_product_domain(raw_idea=raw_idea, brief=brief)
    profile = DOMAIN_PROFILES[domain]
    product_brief = _build_product_brief(raw_idea=raw_idea, brief=brief, profile=profile)
    prioritization = _build_prioritization(brief=brief, profile=profile)
    roadmap = _build_roadmap(
        brief=brief,
        profile=profile,
        prioritization=prioritization,
    )
    product_memory = ProductMemoryDocument(
        source_idea=raw_idea,
        product_brief=product_brief,
        generator_decisions=_generator_decisions(
            selected_template_key=selected_template_key,
            domain=domain,
            prioritization=prioritization,
        ),
        selected_template=selected_template_key,
        domain=domain,
        change_history=[
            "Initial idea captured.",
            "Product brief generated.",
            "Feature priorities generated.",
            "Evolution roadmap generated.",
        ],
        feature_prioritization=prioritization,
        roadmap=roadmap,
    )
    return ProductIntelligence(
        product_brief=product_brief,
        feature_prioritization=prioritization,
        roadmap=roadmap,
        product_memory=product_memory,
    )


def load_product_intelligence(
    *,
    payload: Mapping[str, Any],
    raw_idea: str,
    brief: ProjectBrief,
    selected_template_key: str | None,
) -> ProductIntelligence:
    product_brief = payload.get("product_brief")
    feature_prioritization = payload.get("feature_prioritization")
    roadmap = payload.get("roadmap")
    product_memory = payload.get("product_memory")

    if (
        isinstance(product_brief, Mapping)
        and isinstance(feature_prioritization, Mapping)
        and isinstance(roadmap, Mapping)
        and isinstance(product_memory, Mapping)
    ):
        return ProductIntelligence(
            product_brief=ProductBriefDocument.model_validate(dict(product_brief)),
            feature_prioritization=FeaturePrioritization.model_validate(
                dict(feature_prioritization)
            ),
            roadmap=ProjectRoadmap.model_validate(dict(roadmap)),
            product_memory=ProductMemoryDocument.model_validate(dict(product_memory)),
        )

    return build_product_intelligence(
        raw_idea=raw_idea,
        brief=brief,
        selected_template_key=selected_template_key,
    )


def product_intelligence_prompt_items(intelligence: ProductIntelligence) -> list[str]:
    brief = intelligence.product_brief
    priorities = intelligence.feature_prioritization
    roadmap = intelligence.roadmap
    return [
        (
            f"Product brief: {brief.product_name}. Value proposition: "
            f"{brief.value_proposition}. MVP scope: {', '.join(brief.mvp_scope)}."
        ),
        (
            "Feature priorities: "
            f"Must Have: {', '.join(priorities.must_have)}. "
            f"Should Have: {', '.join(priorities.should_have)}. "
            f"Could Have: {', '.join(priorities.could_have)}. "
            f"Future: {', '.join(priorities.future)}."
        ),
        (
            "Project roadmap: "
            + " | ".join(
                f"{phase.name}: {', '.join(phase.features)}" for phase in roadmap.phases
            )
        ),
        (
            "Product memory: "
            f"domain={intelligence.product_memory.domain}; "
            f"template={intelligence.product_memory.selected_template}; "
            f"decisions={'; '.join(intelligence.product_memory.generator_decisions)}."
        ),
    ]


def detect_product_domain(*, raw_idea: str, brief: ProjectBrief) -> str:
    haystack = _normalized_text(
        " ".join(
            [
                raw_idea,
                brief.title,
                brief.goal,
                *brief.target_users,
                *brief.must_have_features,
            ]
        )
    )
    best_key = "generic"
    best_score = 0
    for key, profile in DOMAIN_PROFILES.items():
        if key == "generic":
            continue
        score = sum(1 for keyword in profile.keywords if keyword in haystack)
        if score > best_score:
            best_key = key
            best_score = score
    return best_key


def _build_product_brief(
    *,
    raw_idea: str,
    brief: ProjectBrief,
    profile: ProductDomainProfile,
) -> ProductBriefDocument:
    core_features = _unique([*brief.must_have_features, *profile.must_have])
    mvp_scope = _unique([*core_features, "dashboard", "basic reporting"])[:6]
    return ProductBriefDocument(
        product_name=brief.title,
        target_audience=_unique([*brief.target_users, *profile.target_audience]),
        user_problems=list(profile.problems),
        value_proposition=_value_proposition(raw_idea=raw_idea, brief=brief, profile=profile),
        core_features=core_features,
        mvp_scope=mvp_scope,
        monetization=list(profile.monetization),
        risks=list(profile.risks),
        success_metrics=list(profile.metrics),
    )


def _build_prioritization(
    *,
    brief: ProjectBrief,
    profile: ProductDomainProfile,
) -> FeaturePrioritization:
    must_have = _unique([*brief.must_have_features, *profile.must_have])[:6]
    return FeaturePrioritization(
        must_have=must_have,
        should_have=_unique(profile.should_have),
        could_have=_unique(profile.could_have),
        future=_unique(profile.future),
    )


def _build_roadmap(
    *,
    brief: ProjectBrief,
    profile: ProductDomainProfile,
    prioritization: FeaturePrioritization,
) -> ProjectRoadmap:
    return ProjectRoadmap(
        phases=[
            RoadmapPhase(
                name="Phase 1 - MVP",
                goals=[
                    f"Launch a usable MVP for {brief.title}.",
                    "Validate the core workflow with real users.",
                ],
                features=prioritization.must_have,
                metrics=list(profile.metrics[:2]),
            ),
            RoadmapPhase(
                name="Phase 2 - Growth",
                goals=[
                    "Improve activation and retention.",
                    "Add workflows that reduce manual operations.",
                ],
                features=prioritization.should_have,
                metrics=list(profile.metrics),
            ),
            RoadmapPhase(
                name="Phase 3 - Scale",
                goals=[
                    "Expand automation and analytics.",
                    "Prepare the product for larger teams and paid plans.",
                ],
                features=prioritization.future,
                metrics=[*profile.metrics, "paid conversion rate"],
            ),
        ]
    )


def _value_proposition(
    *,
    raw_idea: str,
    brief: ProjectBrief,
    profile: ProductDomainProfile,
) -> str:
    audience = ", ".join(_unique([*brief.target_users, *profile.target_audience])[:3])
    return (
        f"{brief.title} helps {audience} turn '{raw_idea}' into a focused operating "
        "system with clear records, priorities and measurable outcomes."
    )


def _generator_decisions(
    *,
    selected_template_key: str | None,
    domain: str,
    prioritization: FeaturePrioritization,
) -> list[str]:
    template = selected_template_key or "none"
    return [
        f"Template selected: {template}",
        f"Domain detected: {domain}",
        "Product brief generated before application generation.",
        "MVP scope limited to must-have features.",
        f"Must-have features: {', '.join(prioritization.must_have)}",
    ]


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _unique(values: list[str] | tuple[str, ...]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _normalized_text(str(value))
        if not normalized or normalized in seen:
            continue
        result.append(str(value).strip())
        seen.add(normalized)
    return result
