from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from vuls.reference_analysis import ReferenceAnalysis
from vuls.reference_image_intelligence import ReferenceImageAnalysis
from vuls.reference_product_intelligence import ReferenceProductAnalysis


class UserGoal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    goal: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class UserFlowStep(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    step_number: int = Field(ge=1)
    screen_name: str = Field(min_length=1)
    action: str = Field(min_length=1)


class CoreScreen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)


class NavigationPattern(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    pattern: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class ReferenceUXInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    reference_analysis: ReferenceAnalysis | None = None
    reference_product_analysis: ReferenceProductAnalysis | None = None
    image_analysis: ReferenceImageAnalysis | None = None
    user_intent: str | None = None
    domain: str | None = None
    platform: str | None = None


class ReferenceUXAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    primary_goal: str = Field(min_length=1)
    user_goals: list[UserGoal] = Field(default_factory=list)
    user_flows: list[UserFlowStep] = Field(default_factory=list)
    core_screens: list[CoreScreen] = Field(default_factory=list)
    navigation_patterns: list[NavigationPattern] = Field(default_factory=list)
    onboarding_flow: list[str] = Field(default_factory=list)
    retention_loop: list[str] = Field(default_factory=list)
    reasoning: str = Field(min_length=1)


@dataclass(frozen=True)
class UXProfile:
    product_type: str
    keywords: tuple[str, ...]
    primary_goal: str
    core_screens: tuple[tuple[str, str], ...]
    user_flow: tuple[tuple[str, str], ...]
    onboarding_flow: tuple[str, ...]
    retention_loop: tuple[str, ...]
    navigation_patterns: tuple[tuple[str, str], ...]


UX_PROFILES: tuple[UXProfile, ...] = (
    UXProfile(
        product_type="SaaS Workspace",
        keywords=(
            "saas",
            "workspace",
            "teamly",
            "documents",
            "team members",
            "billing",
        ),
        primary_goal="Manage team knowledge",
        core_screens=(
            ("Workspace", "Choose the active team workspace and current work context."),
            ("Dashboard", "Show workspace activity, shortcuts, and next actions."),
            ("Documents", "Create, find, edit, and organize shared knowledge."),
            ("Team", "Manage members, permissions, and collaboration state."),
            ("Billing", "Review subscription, invoices, and plan limits."),
            ("Settings", "Configure workspace preferences and account controls."),
        ),
        user_flow=(
            ("Login", "Sign in"),
            ("Workspace", "Choose workspace"),
            ("Document", "Open document"),
            ("Editor", "Edit document"),
            ("Share", "Share with team"),
            ("Comments", "Discuss changes"),
            ("Saved", "Save knowledge"),
        ),
        onboarding_flow=("Sign up", "Create workspace", "Invite team", "Create document"),
        retention_loop=("Create", "Collaborate", "Update", "Return"),
        navigation_patterns=(
            ("workspace-first", "The user starts by choosing a team workspace context."),
            ("sidebar-first", "Persistent product areas need fast left navigation."),
            ("search-first", "Documents and team knowledge need quick retrieval."),
        ),
    ),
    UXProfile(
        product_type="CRM",
        keywords=("crm", "customers", "deals", "pipeline", "leads", "reports"),
        primary_goal="Manage customers and deals",
        core_screens=(
            ("Dashboard", "Summarize pipeline, tasks, and sales health."),
            ("Customers", "View customer records, activity, and owner context."),
            ("Deals", "Move opportunities through pipeline stages."),
            ("Reports", "Review conversion, revenue, and team performance."),
            ("Settings", "Configure fields, stages, and team access."),
        ),
        user_flow=(
            ("Dashboard", "Review pipeline"),
            ("Leads", "Add lead"),
            ("Customer", "Open customer record"),
            ("Deal", "Update deal stage"),
            ("Report", "Track results"),
        ),
        onboarding_flow=("Import customers", "Configure pipeline", "Add first deal"),
        retention_loop=("Capture leads", "Manage deals", "Track results", "Return"),
        navigation_patterns=(
            ("dashboard-first", "CRM users need a fast operational overview."),
            ("table-first", "Customer and deal records benefit from sortable lists."),
        ),
    ),
    UXProfile(
        product_type="Learning Platform",
        keywords=(
            "learning",
            "courses",
            "lessons",
            "quiz",
            "progress",
            "achievements",
        ),
        primary_goal="Learn lessons and track progress",
        core_screens=(
            ("Lessons", "Browse and continue learning content."),
            ("Progress", "Show completion, streak, and learning status."),
            ("Achievements", "Reward milestones and reinforce motivation."),
            ("Profile", "Personalize learning goals and account state."),
            ("Settings", "Configure reminders and preferences."),
        ),
        user_flow=(
            ("Home", "Choose lesson"),
            ("Lesson", "Learn concept"),
            ("Quiz", "Answer questions"),
            ("Result", "Review outcome"),
            ("Progress", "Track progress"),
        ),
        onboarding_flow=("Sign up", "Choose course", "Start lesson"),
        retention_loop=("Learn", "Progress", "Achievement", "Return"),
        navigation_patterns=(
            ("content-first", "Learners should resume or start lessons quickly."),
            ("dashboard-first", "Progress feedback motivates the next session."),
        ),
    ),
    UXProfile(
        product_type="Dashboard",
        keywords=("dashboard", "analytics", "metrics", "reports", "filters", "kpi"),
        primary_goal="Monitor metrics and act on insights",
        core_screens=(
            ("Dashboard", "Summarize the current state and key exceptions."),
            ("Analytics", "Explore metric trends and drivers."),
            ("Reports", "Review periodic results and shareable summaries."),
            ("Search", "Find records, filters, and focused views."),
            ("Settings", "Configure data, permissions, and alerts."),
        ),
        user_flow=(
            ("Dashboard", "Scan metrics"),
            ("Filter", "Narrow context"),
            ("Insight", "Inspect detail"),
            ("Action", "Take next action"),
            ("Report", "Share result"),
        ),
        onboarding_flow=("Connect data", "Choose metrics", "Review dashboard"),
        retention_loop=("Monitor", "Investigate", "Act", "Return"),
        navigation_patterns=(
            ("dashboard-first", "The overview is the main decision surface."),
            ("sidebar-first", "Reports and filters need persistent navigation."),
        ),
    ),
)


def analyze_reference_ux(ux_input: ReferenceUXInput) -> ReferenceUXAnalysis:
    haystack = _ux_haystack(ux_input)
    if not haystack:
        return _empty_analysis()

    profile, match_count = _detect_profile(ux_input, haystack)
    if profile is None:
        return _empty_analysis()

    confidence = _goal_confidence(ux_input, match_count)
    return ReferenceUXAnalysis(
        primary_goal=profile.primary_goal,
        user_goals=[
            UserGoal(goal=profile.primary_goal, confidence=confidence),
        ],
        user_flows=_flow_steps(profile.user_flow),
        core_screens=[
            CoreScreen(name=name, purpose=purpose)
            for name, purpose in profile.core_screens
        ],
        navigation_patterns=_navigation_patterns(profile, haystack),
        onboarding_flow=list(profile.onboarding_flow),
        retention_loop=list(profile.retention_loop),
        reasoning=(
            f"Detected {profile.product_type} UX from reference product and "
            f"{match_count} UX keyword signal(s)."
        ),
    )


def load_reference_ux_analysis(
    *,
    payload: Mapping[str, Any],
    reference_analysis: ReferenceAnalysis | None = None,
    reference_product_analysis: ReferenceProductAnalysis | None = None,
    image_analysis: ReferenceImageAnalysis | None = None,
    user_intent: str | None = None,
    domain: str | None = None,
    platform: str | None = None,
) -> ReferenceUXAnalysis | None:
    existing = payload.get("reference_ux_analysis")
    if isinstance(existing, Mapping):
        return ReferenceUXAnalysis.model_validate(dict(existing))
    if reference_analysis is None and isinstance(payload.get("reference_analysis"), Mapping):
        reference_analysis = ReferenceAnalysis.model_validate(
            dict(payload["reference_analysis"])
        )
    if reference_product_analysis is None and isinstance(
        payload.get("reference_product_analysis"), Mapping
    ):
        reference_product_analysis = ReferenceProductAnalysis.model_validate(
            dict(payload["reference_product_analysis"])
        )
    if image_analysis is None and isinstance(payload.get("reference_image_analysis"), Mapping):
        image_analysis = ReferenceImageAnalysis.model_validate(
            dict(payload["reference_image_analysis"])
        )
    if image_analysis is None:
        return None

    analysis = analyze_reference_ux(
        ReferenceUXInput(
            reference_analysis=reference_analysis,
            reference_product_analysis=reference_product_analysis,
            image_analysis=image_analysis,
            user_intent=user_intent,
            domain=domain,
            platform=platform,
        )
    )
    return None if analysis.primary_goal == "Unknown" else analysis


def reference_ux_analysis_prompt_items(analysis: ReferenceUXAnalysis) -> list[str]:
    items = [
        (
            "Reference UX Intelligence: "
            f"primary_goal={analysis.primary_goal}; "
            f"reasoning={analysis.reasoning}"
        )
    ]
    if analysis.core_screens:
        items.append(
            "UX core screens: "
            + "; ".join(
                f"{screen.name} ({screen.purpose})" for screen in analysis.core_screens
            )
        )
    if analysis.user_flows:
        items.append(
            "UX user flow: "
            + " -> ".join(step.screen_name for step in analysis.user_flows)
        )
    if analysis.navigation_patterns:
        items.append(
            "UX navigation patterns: "
            + ", ".join(pattern.pattern for pattern in analysis.navigation_patterns)
        )
    if analysis.onboarding_flow:
        items.append("UX onboarding flow: " + " -> ".join(analysis.onboarding_flow))
    if analysis.retention_loop:
        items.append("UX retention loop: " + " -> ".join(analysis.retention_loop))
    return items


def _detect_profile(
    ux_input: ReferenceUXInput,
    haystack: str,
) -> tuple[UXProfile | None, int]:
    direct_context = _normalized_text(
        " ".join([ux_input.user_intent or "", ux_input.domain or ""])
    )
    direct_profile, direct_score = _best_keyword_profile(direct_context)
    if direct_profile is not None:
        return direct_profile, direct_score

    if ux_input.reference_product_analysis is not None:
        product_type = ux_input.reference_product_analysis.product_type
        for profile in UX_PROFILES:
            if profile.product_type == product_type:
                return profile, _keyword_score(haystack, profile.keywords)

    return _best_keyword_profile(haystack)


def _best_keyword_profile(text: str) -> tuple[UXProfile | None, int]:
    best_profile: UXProfile | None = None
    best_score = 0
    for profile in UX_PROFILES:
        score = _keyword_score(text, profile.keywords)
        if score > best_score:
            best_profile = profile
            best_score = score
    return best_profile, best_score


def _navigation_patterns(profile: UXProfile, haystack: str) -> list[NavigationPattern]:
    patterns = [
        NavigationPattern(pattern=pattern, reason=reason)
        for pattern, reason in profile.navigation_patterns
    ]
    additions = {
        "sidebar-first": (
            ("sidebar", "left navigation", "left nav", "navigation rail"),
            "Reference signals mention persistent sidebar or left navigation.",
        ),
        "tab navigation": (
            ("tab navigation", "tabs", "tab bar", "bottom navigation"),
            "Reference signals mention tabbed navigation or bottom tab controls.",
        ),
        "search-first": (
            ("search", "command palette", "filter"),
            "Reference signals mention search, filtering, or quick retrieval.",
        ),
        "content-first": (
            ("lesson", "lessons", "document", "documents", "content", "course"),
            "Reference signals make content objects the main user destination.",
        ),
    }
    existing = {pattern.pattern for pattern in patterns}
    for pattern, (keywords, reason) in additions.items():
        if pattern in existing:
            continue
        if any(_has_keyword(haystack, keyword) for keyword in keywords):
            patterns.append(NavigationPattern(pattern=pattern, reason=reason))
            existing.add(pattern)
    return patterns


def _flow_steps(flow: tuple[tuple[str, str], ...]) -> list[UserFlowStep]:
    return [
        UserFlowStep(step_number=index, screen_name=screen, action=action)
        for index, (screen, action) in enumerate(flow, start=1)
    ]


def _goal_confidence(ux_input: ReferenceUXInput, match_count: int) -> float:
    if ux_input.reference_product_analysis is not None:
        return min(0.95, ux_input.reference_product_analysis.confidence + 0.04)
    return min(0.9, 0.5 + match_count * 0.08)


def _keyword_score(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if _has_keyword(text, keyword))


def _ux_haystack(ux_input: ReferenceUXInput) -> str:
    parts = [
        ux_input.user_intent or "",
        ux_input.domain or "",
        ux_input.platform or "",
    ]
    if ux_input.reference_product_analysis is not None:
        product = ux_input.reference_product_analysis
        parts.extend(
            [
                product.product_type,
                product.reasoning,
                " ".join(feature.name for feature in product.detected_features),
                " ".join(pattern.pattern_name for pattern in product.detected_patterns),
                " ".join(product.suggested_product_structure),
            ]
        )
    if ux_input.reference_analysis is not None:
        parts.append(ux_input.reference_analysis.summary)
        for signals in (
            ux_input.reference_analysis.mood_signals,
            ux_input.reference_analysis.composition_signals,
            ux_input.reference_analysis.visual_quality_signals,
            ux_input.reference_analysis.interaction_signals,
            ux_input.reference_analysis.platform_signals,
        ):
            parts.extend(_signal_parts(signal) for signal in signals)
    if ux_input.image_analysis is not None:
        parts.append(ux_input.image_analysis.summary)
        for image_signals in (
            ux_input.image_analysis.composition_signals,
            ux_input.image_analysis.color_signals,
            ux_input.image_analysis.density_signals,
            ux_input.image_analysis.platform_signals,
            ux_input.image_analysis.quality_signals,
        ):
            parts.extend(_signal_parts(signal) for signal in image_signals)
    return _normalized_text(" ".join(parts))


def _signal_parts(signal: Any) -> str:
    return " ".join(
        [
            str(getattr(signal, "signal_type", "")),
            str(getattr(signal, "value", "")),
            str(getattr(signal, "rationale", "")),
        ]
    )


def _empty_analysis() -> ReferenceUXAnalysis:
    return ReferenceUXAnalysis(
        primary_goal="Unknown",
        reasoning=(
            "No reference UX signals were available; keep using Product and Design "
            "Intelligence as the source of truth."
        ),
    )


def _has_keyword(text: str, keyword: str) -> bool:
    normalized_keyword = _normalized_text(keyword)
    if " " in normalized_keyword:
        return normalized_keyword in text
    return re.search(rf"\b{re.escape(normalized_keyword)}\b", text) is not None


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()
