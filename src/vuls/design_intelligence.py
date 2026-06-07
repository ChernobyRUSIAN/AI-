# ruff: noqa: E501
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from vuls.product_intelligence import ProductBriefDocument
from vuls.reference_analysis import ReferenceAnalysis

DesignPlatform = Literal["telegram_mini_app", "web", "mobile"]


class DesignInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    product_brief: ProductBriefDocument
    domain: str = Field(min_length=1)
    user_prompt: str = Field(min_length=1)
    references: list[str] = Field(default_factory=list)
    reference_analysis: ReferenceAnalysis | None = None
    desired_emotion: str | None = None
    platform: DesignPlatform = "web"


class DesignArchetype(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class VisualSystem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    color_system: str = Field(min_length=1)
    typography_direction: str = Field(min_length=1)
    spacing_radius_system: str = Field(min_length=1)
    motion_direction: str = Field(min_length=1)


class ComponentRules(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    primary_components: list[str] = Field(min_length=1)
    interaction_rules: list[str] = Field(min_length=1)
    forbidden_patterns: list[str] = Field(min_length=1)


class OpenDesignBrief(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    prompt: str = Field(min_length=1)
    inspiration_signals: list[str] = Field(default_factory=list)
    negative_constraints: list[str] = Field(min_length=1)


class DesignContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    domain: str = Field(min_length=1)
    platform: DesignPlatform
    visual_archetype: DesignArchetype
    product_emotion: str = Field(min_length=1)
    hero_object_strategy: str = Field(min_length=1)
    screen_composition: str = Field(min_length=1)
    visual_hierarchy: str = Field(min_length=1)
    surface_model: str = Field(min_length=1)
    visual_system: VisualSystem
    component_rules: ComponentRules
    ux_rules: list[str] = Field(min_length=1)
    open_design_brief: OpenDesignBrief


def build_design_contract(design_input: DesignInput) -> DesignContract:
    profile = _profile_with_reference_signals(
        _select_profile(design_input),
        _reference_signal_types(design_input.reference_analysis),
    )
    platform_rules = _platform_rules(design_input.platform)
    references = _clean_references(design_input.references)
    reference_signals = _reference_signal_types(design_input.reference_analysis)
    product_emotion = _product_emotion(
        default=profile["emotion"],
        desired_emotion=design_input.desired_emotion,
    )
    screen_composition = f"{profile['composition']} {platform_rules['composition']}"
    interaction_rules = [*profile["interaction_rules"], *platform_rules["interaction_rules"]]
    ux_rules = [*profile["ux_rules"], *platform_rules["ux_rules"]]
    negative_constraints = _negative_constraints(
        references=references,
        reference_analysis=design_input.reference_analysis,
    )
    prompt = _open_design_prompt(
        design_input=design_input,
        profile=profile,
        product_emotion=product_emotion,
        screen_composition=screen_composition,
        interaction_rules=interaction_rules,
        ux_rules=ux_rules,
        references=references,
        reference_signals=reference_signals,
        negative_constraints=negative_constraints,
    )

    return DesignContract(
        domain=design_input.domain,
        platform=design_input.platform,
        visual_archetype=DesignArchetype(
            key=profile["key"],
            label=profile["label"],
            rationale=profile["rationale"],
        ),
        product_emotion=product_emotion,
        hero_object_strategy=profile["hero_object"],
        screen_composition=screen_composition,
        visual_hierarchy=profile["hierarchy"],
        surface_model=profile["surface_model"],
        visual_system=VisualSystem(
            color_system=profile["color_system"],
            typography_direction=profile["typography"],
            spacing_radius_system=profile["spacing_radius"],
            motion_direction=profile["motion"],
        ),
        component_rules=ComponentRules(
            primary_components=profile["components"],
            interaction_rules=interaction_rules,
            forbidden_patterns=[
                "Do not copy a reference screen.",
                "Do not use a fixed branded template.",
                "Do not make a generic CRUD or CRM shell when the product needs a stronger visual direction.",
            ],
        ),
        ux_rules=ux_rules,
        open_design_brief=OpenDesignBrief(
            prompt=prompt,
            inspiration_signals=[*references, *reference_signals],
            negative_constraints=negative_constraints,
        ),
    )


def load_design_contract(
    *,
    payload: Mapping[str, Any],
    product_brief: ProductBriefDocument,
    domain: str,
    user_prompt: str,
    platform: DesignPlatform = "web",
    references: list[str] | None = None,
    reference_analysis: ReferenceAnalysis | None = None,
    desired_emotion: str | None = None,
) -> DesignContract:
    existing = payload.get("design_contract")
    if isinstance(existing, Mapping):
        return DesignContract.model_validate(dict(existing))

    if reference_analysis is None and isinstance(payload.get("reference_analysis"), Mapping):
        reference_analysis = ReferenceAnalysis.model_validate(dict(payload["reference_analysis"]))

    return build_design_contract(
        DesignInput(
            product_brief=product_brief,
            domain=domain,
            user_prompt=user_prompt,
            references=references or [],
            reference_analysis=reference_analysis,
            desired_emotion=desired_emotion,
            platform=platform,
        )
    )


def design_contract_prompt_items(contract: DesignContract) -> list[str]:
    return [
        (
            "Design Intelligence: "
            f"archetype={contract.visual_archetype.key}; "
            f"emotion={contract.product_emotion}; "
            f"hero={contract.hero_object_strategy}; "
            f"composition={contract.screen_composition}; "
            f"hierarchy={contract.visual_hierarchy}."
        ),
        (
            "Visual system: "
            f"colors={contract.visual_system.color_system}; "
            f"typography={contract.visual_system.typography_direction}; "
            f"spacing={contract.visual_system.spacing_radius_system}; "
            f"surfaces={contract.surface_model}; "
            f"motion={contract.visual_system.motion_direction}."
        ),
        (
            "Component and UX rules: "
            f"components={'; '.join(contract.component_rules.primary_components)}; "
            f"interactions={'; '.join(contract.component_rules.interaction_rules)}; "
            f"ux={'; '.join(contract.ux_rules)}."
        ),
        f"Open Design prompt: {contract.open_design_brief.prompt}",
    ]


def _select_profile(design_input: DesignInput) -> dict[str, Any]:
    text = _haystack(design_input)
    if _has_any(text, ("fitness", "gym", "trainer", "workout", "member", "membership")):
        return _profile(
            key="gamified_reward_interface",
            label="Gamified reward interface",
            rationale="Fitness products need motivation, progress loops, and energetic operational clarity.",
            emotion="energetic, motivating, premium, confident",
            hero_object="Member progress pulse with streaks, class readiness, retention risk, and next best action.",
            composition="Mobile-first command surface with a strong progress hero, compact KPI strip, and action queues.",
            hierarchy="Lead with progress and motivation, then surface today's member, class, and revenue actions.",
            surface_model="Layered premium cards over a focused app shell; reward surfaces should feel alive but not childish.",
            color_system="Energetic contrast with fresh accent colors, controlled dark/light balance, and status colors for risk and progress.",
            typography="Bold numeric display type for progress, clean sans text for operational scanning.",
            spacing_radius="Compact rhythm, medium radii, touch-friendly controls, and consistent card spacing.",
            motion="Subtle progress, streak, and completion motion; avoid noisy game animation.",
            components=[
                "progress hero",
                "streak or momentum indicator",
                "member action queue",
                "class capacity cards",
                "retention risk states",
            ],
            interaction_rules=[
                "Make the primary action reachable with one thumb movement.",
                "Use reward feedback for completed tasks and member milestones.",
            ],
            ux_rules=[
                "Prioritize member motivation and staff follow-up over generic record tables.",
                "Show empty, risk, and completed states for progress-driven flows.",
            ],
        )
    if _has_any(text, ("dentistry", "dental", "dentist", "clinic", "patient", "treatment")):
        return _profile(
            key="clean_medical_dashboard",
            label="Clean medical dashboard",
            rationale="Clinical operations need trust, legibility, triage, and calm urgency.",
            emotion="calm, precise, trustworthy, clinically focused",
            hero_object="Clinic day risk board showing chair utilization, recall gaps, claims, and patient follow-ups.",
            composition="Quiet dashboard with triage summary, care workflow lanes, and dense but readable patient context.",
            hierarchy="Lead with operational risk, then appointments, treatment plans, insurance, and follow-up tasks.",
            surface_model="Clean white and soft-tint surfaces with crisp borders, restrained shadows, and clear status chips.",
            color_system="Medical neutral base with blue/green trust accents and restrained amber/red risk states.",
            typography="Highly legible sans typography with tabular numerics for clinical metrics.",
            spacing_radius="Regular spacing, low-to-medium radius, and calm separation between data groups.",
            motion="Minimal motion for state changes only; no playful transitions.",
            components=[
                "clinic snapshot hero",
                "risk KPI cards",
                "appointment lanes",
                "treatment plan table",
                "insurance queue",
            ],
            interaction_rules=[
                "Keep patient actions explicit and low ambiguity.",
                "Use severity ordering for time-sensitive clinical work.",
            ],
            ux_rules=[
                "Optimize for scanning under front-desk pressure.",
                "Separate patient care, billing, and schedule concerns visually.",
            ],
        )
    if _has_any(
        text,
        (
            "technical",
            "control",
            "drone",
            "iot",
            "device",
            "logistics",
            "fleet",
            "route",
            "tracking",
        ),
    ):
        return _profile(
            key="dark_technical_control_center",
            label="Dark technical control center",
            rationale="Technical operations need telemetry, command confidence, and spatial awareness.",
            emotion="focused, high-control, precise, technical",
            hero_object="Live system object with telemetry, route, device, or operational state wrapped by controls.",
            composition="Control-center layout with status map, telemetry cards, command rail, and event stream.",
            hierarchy="Lead with live state and exceptions, then expose controls, diagnostics, and recent events.",
            surface_model="Dark glass-like operational panels, thin borders, and high-contrast telemetry modules.",
            color_system="Deep neutral base with cyan/green signal colors, warning amber, and restrained danger red.",
            typography="Compact technical sans with tabular numerics and clear labels.",
            spacing_radius="Dense spacing, small-to-medium radii, aligned telemetry grids.",
            motion="Low-latency signal motion for live updates, route progress, and alert state changes.",
            components=[
                "live object hero",
                "telemetry cards",
                "control rail",
                "map or path panel",
                "event log",
            ],
            interaction_rules=[
                "Make critical controls visually distinct from passive telemetry.",
                "Prefer progressive disclosure for advanced diagnostics.",
            ],
            ux_rules=[
                "Prioritize current state, risk, and next action over CRUD lists.",
                "Design for rapid operator scanning in low-light contexts.",
            ],
        )
    if _has_any(text, ("farm", "agriculture", "nature", "field", "crop", "forest")):
        return _profile(
            key="calm_nature_operations_ui",
            label="Calm nature operations UI",
            rationale="Nature and field operations need ambient clarity, spatial context, and calm stewardship.",
            emotion="calm, grounded, organic, attentive",
            hero_object="Living field or territory map with health, weather, resource, and task overlays.",
            composition="Map-led operations surface with environmental metrics, field segments, and gentle action cards.",
            hierarchy="Lead with land state, then weather/resource risks, then tasks and observations.",
            surface_model="Soft translucent panels over natural imagery or map-like regions; avoid decorative clutter.",
            color_system="Natural greens and earth neutrals with accessible contrast and clear risk accents.",
            typography="Warm but precise sans typography with readable environmental numerics.",
            spacing_radius="Comfortable spacing, medium radii, and organic grouping without losing alignment.",
            motion="Slow ambient transitions for environment changes; direct feedback for task updates.",
            components=[
                "field map hero",
                "environment metric cards",
                "resource health panels",
                "observation timeline",
                "task overlays",
            ],
            interaction_rules=[
                "Keep map and environment context visible during decisions.",
                "Use calm state transitions for changing conditions.",
            ],
            ux_rules=[
                "Frame operations as stewardship, not generic task management.",
                "Make weather, resource, and risk context immediately visible.",
            ],
        )
    return _profile(
        key="premium_operations_ui",
        label="Premium operations UI",
        rationale="The product needs modern app quality while preserving operational clarity.",
        emotion="clear, capable, polished, modern",
        hero_object="Product-specific operating object that summarizes status, progress, and next action.",
        composition="Premium dashboard with a strong product hero, contextual modules, and focused action areas.",
        hierarchy="Lead with product outcome, then operational signals, work queues, and supporting data.",
        surface_model="Clean layered surfaces with restrained depth, crisp borders, and purposeful empty states.",
        color_system="Balanced neutral foundation with one confident accent and semantic status colors.",
        typography="Modern sans typography with strong hierarchy and readable dense data.",
        spacing_radius="Consistent spacing, medium radii, and stable dimensions for repeated modules.",
        motion="Subtle motion for state transitions, confirmations, and progressive disclosure.",
        components=[
            "product outcome hero",
            "KPI modules",
            "priority queue",
            "detail panels",
            "stateful empty/error/success views",
        ],
        interaction_rules=[
            "Keep primary actions visually available without overwhelming the workspace.",
            "Use controls that match the task: toggles, segmented controls, filters, and menus.",
        ],
        ux_rules=[
            "Avoid a plain CRUD shell; every screen should express the product's operating model.",
            "Make each module explain what the user can decide or do next.",
        ],
    )


def _profile_with_reference_signals(
    profile: dict[str, Any],
    signal_types: list[str],
) -> dict[str, Any]:
    signals = set(signal_types)
    if (
        "gamified_reward_loop" in signals
        and "dark_technical_control" not in signals
        and profile["key"] != "clean_medical_dashboard"
    ):
        return _profile(
            key="gamified_reward_interface",
            label="Gamified reward interface",
            rationale="Reference signals point to motivation loops, progress feedback, and reward moments.",
            emotion="energetic, rewarding, premium, motivating",
            hero_object="Progress-and-reward hero showing streak state, next milestone, and one clear action.",
            composition="Mobile-first reward surface with a progress hero, momentum indicators, and focused action cards.",
            hierarchy="Lead with progress and motivation, then surface the next action and supporting activity.",
            surface_model="Layered premium cards with energetic reward states; avoid childish or branded game styling.",
            color_system="Energetic contrast with fresh accents, semantic progress colors, and restrained neutral grounding.",
            typography="Bold display numerics for progress and clean sans text for task clarity.",
            spacing_radius="Compact rhythm, medium radii, touch-friendly controls, and stable reward modules.",
            motion="Subtle reward, streak, and completion motion without noisy game animation.",
            components=[
                "progress hero",
                "streak or momentum indicator",
                "next-action card",
                "achievement state",
                "activity queue",
            ],
            interaction_rules=[
                "Make reward feedback quick and product-specific.",
                "Keep the primary action reachable with one thumb movement.",
            ],
            ux_rules=[
                "Use motivation loops to clarify what the user should do next.",
                "Never copy a named gamified app's mascot, layout, or brand system.",
            ],
        )

    adjusted = dict(profile)
    if "premium_depth" in signals:
        adjusted["surface_model"] = (
            f"{adjusted['surface_model']} Use premium depth with restrained layering, "
            "crisp contrast, and careful shadow discipline."
        )
        adjusted["motion"] = (
            f"{adjusted['motion']} Add polished micro-motion for state changes and transitions."
        )
    if "strong_hero_object" in signals:
        adjusted["hero_object"] = (
            "Strong product-specific hero object that communicates state, context, and next action "
            "without copying any reference composition."
        )
        adjusted["hierarchy"] = (
            f"{adjusted['hierarchy']} Keep the hero object as the first visual decision point."
        )
    if "map_first_spatial_context" in signals:
        adjusted["composition"] = (
            f"{adjusted['composition']} Add map-first spatial context where routes, territory, or live position "
            "drive the workflow."
        )
    if "dark_technical_control" in signals and profile["key"] == "premium_operations_ui":
        adjusted["key"] = "dark_technical_control_center"
        adjusted["label"] = "Dark technical control center"
        adjusted["rationale"] = "Reference signals point to telemetry, command confidence, and technical control."
        adjusted["emotion"] = "focused, high-control, precise, technical"
        adjusted["surface_model"] = "Dark operational panels, thin borders, and high-contrast telemetry modules."
        adjusted["color_system"] = "Deep neutral base with cyan/green signal colors and restrained warning states."
    if "clean_medical_trust" in signals and profile["key"] == "premium_operations_ui":
        adjusted["key"] = "clean_medical_dashboard"
        adjusted["label"] = "Clean medical dashboard"
        adjusted["rationale"] = "Reference signals point to clinical trust, risk clarity, and patient context."
        adjusted["emotion"] = "calm, precise, trustworthy, clinically focused"
        adjusted["surface_model"] = "Clean light surfaces, crisp borders, restrained shadows, and clear status chips."
        adjusted["color_system"] = "Medical neutral base with blue/green trust accents and restrained risk states."
    return adjusted


def _open_design_prompt(
    *,
    design_input: DesignInput,
    profile: dict[str, Any],
    product_emotion: str,
    screen_composition: str,
    interaction_rules: list[str],
    ux_rules: list[str],
    references: list[str],
    reference_signals: list[str],
    negative_constraints: list[str],
) -> str:
    brief = design_input.product_brief
    lines = [
        f"Create a premium app UI direction for {brief.product_name}.",
        f"Domain: {design_input.domain}.",
        f"Platform: {design_input.platform.replace('_', ' ')}.",
        f"Visual archetype: {profile['label']} ({profile['key']}).",
        f"Product emotion: {product_emotion}.",
        f"Hero object strategy: {profile['hero_object']}.",
        f"Screen composition: {screen_composition}.",
        f"Visual hierarchy: {profile['hierarchy']}.",
        f"Surface model: {profile['surface_model']}.",
        f"Color system: {profile['color_system']}.",
        f"Typography direction: {profile['typography']}.",
        f"Spacing and radius system: {profile['spacing_radius']}.",
        f"Motion direction: {profile['motion']}.",
        f"Primary components: {'; '.join(profile['components'])}.",
        f"Interaction rules: {'; '.join(interaction_rules)}.",
        f"UX rules: {'; '.join(ux_rules)}.",
        (
            "Reference examples are inspiration signals, not templates. Do not copy layouts, "
            "brand assets, mascots, proprietary UI, or recognizable visual identity from any referenced product."
        ),
    ]
    if references:
        lines.append(f"Inspiration signals: {'; '.join(references)}.")
    if reference_signals:
        lines.append(f"Reference analysis signals: {'; '.join(reference_signals)}.")
    lines.extend(
        [
            f"Negative constraints: {'; '.join(negative_constraints)}.",
            "Generate a direction that feels native to this product instead of copying a known app screen.",
            "The result should guide Open Design toward original React/Next.js/Tailwind-ready UI artifacts.",
        ]
    )
    return " ".join(lines)


def _negative_constraints(
    *,
    references: list[str],
    reference_analysis: ReferenceAnalysis | None,
) -> list[str]:
    constraints = [
        (
            "Reference examples are inspiration signals, not templates. Do not copy layouts, "
            "brand assets, mascots, proprietary UI, or recognizable visual identity from any referenced product."
        ),
        "Do not copy any reference UI.",
        "Do not create a Duolingo template.",
        "Do not create an Apple template.",
        "Do not create a generic health dashboard template.",
        "Do not hard-code a branded visual style from references.",
        "Do not reduce the product to ordinary CRUD or CRM screens.",
    ]
    if references:
        constraints.append("Use references only as inspiration signals for quality, emotion, and interaction density.")
    if reference_analysis is not None:
        constraints.extend(reference_analysis.negative_constraints)
    return _dedupe_strings(constraints)


def _platform_rules(platform: DesignPlatform) -> dict[str, list[str] | str]:
    if platform == "telegram_mini_app":
        return {
            "composition": (
                "Telegram mini app composition: compact, vertical, fast-loading, and thumb-first with sticky primary action zones."
            ),
            "interaction_rules": [
                "Use Telegram mini app safe areas and avoid wide desktop-only layouts.",
                "Keep core decisions thumb-reachable on small screens.",
            ],
            "ux_rules": [
                "Prefer compact progressive disclosure over large multi-column panels.",
                "Make the first screen useful without horizontal scrolling.",
            ],
        }
    if platform == "mobile":
        return {
            "composition": "Mobile composition: single-column flow, bottom actions, and glanceable modules.",
            "interaction_rules": [
                "Use touch-sized controls and predictable bottom navigation.",
                "Avoid dense tables unless transformed into cards.",
            ],
            "ux_rules": [
                "Prioritize one primary task per viewport.",
                "Keep important status visible above the fold.",
            ],
        }
    return {
        "composition": "Web composition: responsive desktop workspace with scalable modules and clear navigation.",
        "interaction_rules": [
            "Use responsive grids that collapse cleanly to mobile.",
            "Support keyboard-friendly controls and accessible focus states.",
        ],
        "ux_rules": [
            "Balance overview density with clear next actions.",
            "Preserve hierarchy across desktop and narrow layouts.",
        ],
    }


def _profile(**kwargs: Any) -> dict[str, Any]:
    return kwargs


def _product_emotion(*, default: str, desired_emotion: str | None) -> str:
    if desired_emotion is None or not desired_emotion.strip():
        return default
    return f"{desired_emotion.strip()}, grounded by {default}"


def _clean_references(references: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for reference in references:
        value = " ".join(reference.split()).strip()
        key = value.casefold()
        if not value or key in seen:
            continue
        cleaned.append(value)
        seen.add(key)
    return cleaned


def _reference_signal_types(reference_analysis: ReferenceAnalysis | None) -> list[str]:
    if reference_analysis is None:
        return []
    signal_types: list[str] = []
    for signals in (
        reference_analysis.mood_signals,
        reference_analysis.composition_signals,
        reference_analysis.visual_quality_signals,
        reference_analysis.interaction_signals,
        reference_analysis.platform_signals,
    ):
        signal_types.extend(signal.signal_type for signal in signals)
    return _dedupe_strings(signal_types)


def _dedupe_strings(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        result.append(value)
        seen.add(key)
    return result


def _haystack(design_input: DesignInput) -> str:
    brief = design_input.product_brief
    return " ".join(
        [
            design_input.domain,
            design_input.user_prompt,
            brief.product_name,
            brief.value_proposition,
            " ".join(brief.target_audience),
            " ".join(brief.core_features),
            " ".join(brief.mvp_scope),
        ]
    ).casefold()


def _has_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)
