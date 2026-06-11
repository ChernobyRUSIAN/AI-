from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from vuls.reference_image_intelligence import ReferenceImageAnalysis

ReferenceSourceKind = Literal[
    "screenshot",
    "moodboard",
    "product_name",
    "url",
    "uploaded_image",
    "text",
]


class ReferenceItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str = Field(min_length=1)
    description: str = ""
    source_kind: ReferenceSourceKind = "text"
    tags: list[str] = Field(default_factory=list)


class ReferenceInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    references: list[ReferenceItem] = Field(default_factory=list)
    image_analysis: ReferenceImageAnalysis | None = None
    user_intent: str | None = None
    domain: str | None = None
    platform: str | None = None


class ReferenceSignal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    signal_type: str = Field(min_length=1)
    value: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)


class ReferenceMood(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    signals: list[ReferenceSignal] = Field(default_factory=list)


class ReferenceComposition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    signals: list[ReferenceSignal] = Field(default_factory=list)


class ReferenceQualityBar(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    signals: list[ReferenceSignal] = Field(default_factory=list)


class ReferenceConstraints(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    negative_constraints: list[str] = Field(default_factory=list)


class ReferenceAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    mood_signals: list[ReferenceSignal] = Field(default_factory=list)
    composition_signals: list[ReferenceSignal] = Field(default_factory=list)
    visual_quality_signals: list[ReferenceSignal] = Field(default_factory=list)
    interaction_signals: list[ReferenceSignal] = Field(default_factory=list)
    platform_signals: list[ReferenceSignal] = Field(default_factory=list)
    negative_constraints: list[str] = Field(default_factory=list)
    summary: str = Field(min_length=1)


REFERENCE_COPY_CONSTRAINT = (
    "Reference examples are inspiration signals, not templates. Do not copy layouts, "
    "brand assets, mascots, proprietary UI, or recognizable visual identity from any "
    "referenced product."
)


def analyze_references(reference_input: ReferenceInput) -> ReferenceAnalysis:
    text = _reference_haystack(reference_input)
    image_signal_types = _reference_image_signal_types(reference_input.image_analysis)
    if not text and not image_signal_types:
        return _empty_analysis()

    mood_signals: list[ReferenceSignal] = []
    composition_signals: list[ReferenceSignal] = []
    visual_quality_signals: list[ReferenceSignal] = []
    interaction_signals: list[ReferenceSignal] = []
    platform_signals: list[ReferenceSignal] = []

    if text:
        _append_text_reference_signals(
            text=text,
            mood_signals=mood_signals,
            composition_signals=composition_signals,
            visual_quality_signals=visual_quality_signals,
            interaction_signals=interaction_signals,
        )
    _append_image_reference_signals(
        signal_types=image_signal_types,
        mood_signals=mood_signals,
        composition_signals=composition_signals,
        visual_quality_signals=visual_quality_signals,
        interaction_signals=interaction_signals,
    )

    return ReferenceAnalysis(
        mood_signals=_dedupe_signals(mood_signals),
        composition_signals=_dedupe_signals(composition_signals),
        visual_quality_signals=_dedupe_signals(visual_quality_signals),
        interaction_signals=_dedupe_signals(interaction_signals),
        platform_signals=_dedupe_signals(platform_signals),
        negative_constraints=_negative_constraints(reference_input.image_analysis),
        summary=_summary(
            mood_signals=mood_signals,
            composition_signals=composition_signals,
            visual_quality_signals=visual_quality_signals,
            interaction_signals=interaction_signals,
            platform_signals=platform_signals,
        ),
    )


def reference_analysis_prompt_items(analysis: ReferenceAnalysis) -> list[str]:
    items = [f"Reference Analysis: {analysis.summary}"]
    for label, signals in (
        ("Mood signals", analysis.mood_signals),
        ("Composition signals", analysis.composition_signals),
        ("Quality bar", analysis.visual_quality_signals),
        ("Interaction signals", analysis.interaction_signals),
        ("Platform signals", analysis.platform_signals),
    ):
        if signals:
            items.append(
                f"{label}: "
                + "; ".join(
                    f"{signal.signal_type}={signal.value}" for signal in signals
                )
            )
    items.append("Reference constraints: " + " ".join(analysis.negative_constraints))
    return items


def load_reference_analysis(
    *,
    payload: Mapping[str, Any],
    domain: str | None = None,
    user_intent: str | None = None,
    platform: str | None = None,
    references: Sequence[str | ReferenceItem] | None = None,
    image_analysis: ReferenceImageAnalysis | None = None,
) -> ReferenceAnalysis:
    existing = payload.get("reference_analysis")
    if isinstance(existing, Mapping):
        return ReferenceAnalysis.model_validate(dict(existing))

    if image_analysis is None and isinstance(payload.get("reference_image_analysis"), Mapping):
        image_analysis = ReferenceImageAnalysis.model_validate(
            dict(payload["reference_image_analysis"])
        )

    return analyze_references(
        ReferenceInput(
            domain=domain,
            user_intent=user_intent,
            platform=platform,
            references=_reference_items(references or ()),
            image_analysis=image_analysis,
        )
    )


def _append_text_reference_signals(
    *,
    text: str,
    mood_signals: list[ReferenceSignal],
    composition_signals: list[ReferenceSignal],
    visual_quality_signals: list[ReferenceSignal],
    interaction_signals: list[ReferenceSignal],
) -> None:
    _append_if_match(
        target=interaction_signals,
        text=text,
        signal_type="gamified_reward_loop",
        keywords=(
            "gamified",
            "streak",
            "streaks",
            "reward",
            "rewards",
            "achievement",
            "celebration",
            "daily goals",
            "progress rings",
            "duolingo",
        ),
        value=(
            "Use progress, streak, milestone, and reward feedback as abstract "
            "motivation patterns."
        ),
        rationale=(
            "Reference language points to habit loops, progress feedback, and reward moments."
        ),
    )
    _append_if_match(
        target=visual_quality_signals,
        text=text,
        signal_type="premium_depth",
        keywords=("premium", "luxury", "immersive", "concierge", "depth", "cinematic"),
        value=(
            "Raise the quality bar with layered depth, careful contrast, and polished "
            "visual rhythm."
        ),
        rationale=(
            "Reference language points to premium perceived quality rather than a flat "
            "CRUD shell."
        ),
    )
    _append_if_match(
        target=composition_signals,
        text=text,
        signal_type="strong_hero_object",
        keywords=(
            "hero",
            "object",
            "destination",
            "aircraft",
            "vehicle",
            "device",
            "product focus",
        ),
        value=(
            "Anchor the first screen around a product-specific object that explains "
            "state and action."
        ),
        rationale=(
            "Reference language points to a dominant focal object instead of a generic "
            "table-first layout."
        ),
    )
    _append_if_match(
        target=mood_signals,
        text=text,
        signal_type="dark_technical_control",
        keywords=(
            "dark",
            "technical",
            "control",
            "telemetry",
            "drone",
            "flight",
            "iot",
            "signal",
            "operator",
        ),
        value="Use a precise command-center composition with telemetry, state, and controls.",
        rationale="Reference language points to technical monitoring and command confidence.",
    )
    _append_if_match(
        target=mood_signals,
        text=text,
        signal_type="calm_operational_clarity",
        keywords=("calm", "clear", "clarity", "operations", "operational", "quiet"),
        value="Keep operations calm, legible, and decision-oriented.",
        rationale="Reference language points to a controlled operational mood.",
    )
    _append_if_match(
        target=mood_signals,
        text=text,
        signal_type="clean_medical_trust",
        keywords=(
            "medical",
            "clinical",
            "health",
            "patient",
            "trust",
            "clinic",
            "risk cards",
            "monitoring",
        ),
        value=(
            "Prefer clean clinical trust, restrained status colors, and high-legibility "
            "data surfaces."
        ),
        rationale=(
            "Reference language points to healthcare trust, patient context, and clinical "
            "clarity."
        ),
    )
    _append_if_match(
        target=composition_signals,
        text=text,
        signal_type="map_first_spatial_context",
        keywords=(
            "map",
            "route",
            "routes",
            "dispatch",
            "location",
            "delivery",
            "vehicle location",
        ),
        value="Lead with spatial context: map, route, location, territory, or movement state.",
        rationale=(
            "Reference language points to geography, routes, and live location as core context."
        ),
    )
    _append_if_match(
        target=visual_quality_signals,
        text=text,
        signal_type="glass_layering",
        keywords=("glass", "glassmorphism", "translucent", "frosted", "layered", "layers"),
        value="Use restrained glass-like layering only where it clarifies depth and state.",
        rationale="Reference language points to layered surfaces and translucent depth.",
    )
    _append_if_match(
        target=interaction_signals,
        text=text,
        signal_type="action_first_hierarchy",
        keywords=("action", "cta", "book", "booking", "next action", "primary action"),
        value="Make the primary decision and next action visually obvious.",
        rationale="Reference language points to action-led hierarchy.",
    )
    _append_if_match(
        target=interaction_signals,
        text=text,
        signal_type="mobile_first_bottom_navigation",
        keywords=("bottom navigation", "bottom nav", "thumb", "one thumb", "mobile tab bar"),
        value="Use mobile-first bottom navigation and thumb-reachable actions when appropriate.",
        rationale="Reference language points to mobile navigation ergonomics.",
    )


def _append_image_reference_signals(
    *,
    signal_types: list[str],
    mood_signals: list[ReferenceSignal],
    composition_signals: list[ReferenceSignal],
    visual_quality_signals: list[ReferenceSignal],
    interaction_signals: list[ReferenceSignal],
) -> None:
    signal_set = set(signal_types)
    if "gamified_character_reference" in signal_set:
        interaction_signals.append(
            ReferenceSignal(
                signal_type="gamified_reward_loop",
                value="Use reward-loop energy from image metadata without copying characters.",
                confidence=0.82,
                rationale="Image reference metadata points to gamified character or reward UI.",
            )
        )
    if "mobile_portrait_reference" in signal_set:
        interaction_signals.append(
            ReferenceSignal(
                signal_type="mobile_first_bottom_navigation",
                value="Use mobile portrait ergonomics and thumb-reachable navigation.",
                confidence=0.78,
                rationale="Image reference metadata points to a portrait mobile interface.",
            )
        )
    if "strong_focal_object" in signal_set or "wide_hero_reference" in signal_set:
        composition_signals.append(
            ReferenceSignal(
                signal_type="strong_hero_object",
                value="Use a product-specific hero object without copying the screenshot.",
                confidence=0.8,
                rationale="Image reference metadata points to a focal object or hero layout.",
            )
        )
    if "technical_control_reference" in signal_set or "dark_interface_reference" in signal_set:
        mood_signals.append(
            ReferenceSignal(
                signal_type="dark_technical_control",
                value="Use focused technical control tone without cloning the reference.",
                confidence=0.84,
                rationale="Image reference metadata points to technical or dark control UI.",
            )
        )
    if "map_or_spatial_reference" in signal_set:
        composition_signals.append(
            ReferenceSignal(
                signal_type="map_first_spatial_context",
                value="Use spatial context where routes or location drive the workflow.",
                confidence=0.8,
                rationale="Image reference metadata points to map or spatial UI.",
            )
        )
    if "medical_clean_reference" in signal_set:
        mood_signals.append(
            ReferenceSignal(
                signal_type="clean_medical_trust",
                value="Use clean clinical trust and legible health data surfaces.",
                confidence=0.82,
                rationale="Image reference metadata points to medical or clinical UI.",
            )
        )
    if "premium_depth_reference" in signal_set:
        visual_quality_signals.append(
            ReferenceSignal(
                signal_type="premium_depth",
                value="Use premium depth and polish as abstract quality signals.",
                confidence=0.8,
                rationale="Image reference metadata points to premium depth or glow.",
            )
        )
    if "glass_layering_reference" in signal_set:
        visual_quality_signals.append(
            ReferenceSignal(
                signal_type="glass_layering",
                value="Use restrained glass layering only where it clarifies depth.",
                confidence=0.78,
                rationale="Image reference metadata points to glass, blur, or translucent layers.",
            )
        )


def _append_if_match(
    *,
    target: list[ReferenceSignal],
    text: str,
    signal_type: str,
    keywords: tuple[str, ...],
    value: str,
    rationale: str,
) -> None:
    matches = sum(1 for keyword in keywords if keyword in text)
    if matches == 0:
        return
    confidence = min(0.95, 0.58 + matches * 0.09)
    target.append(
        ReferenceSignal(
            signal_type=signal_type,
            value=value,
            confidence=confidence,
            rationale=rationale,
        )
    )


def _reference_haystack(reference_input: ReferenceInput) -> str:
    reference_parts: list[str] = []
    for item in reference_input.references:
        reference_parts.extend(
            [
                item.label,
                item.description,
                item.source_kind,
                " ".join(item.tags),
            ]
        )

    context_parts = [
        reference_input.domain or "",
        reference_input.user_intent or "",
        reference_input.platform or "",
    ]
    if not reference_parts:
        context = _normalized_text(" ".join(context_parts))
        return context if _has_explicit_reference_language(context) else ""

    reference_parts.extend(
        context_parts
    )
    return _normalized_text(" ".join(reference_parts))


def _has_explicit_reference_language(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "inspired by",
            "reference",
            "like ",
            "similar to",
            "duolingo",
            "apple fitness",
            "premium app",
            "dark technical",
        )
    )


def _reference_items(values: Sequence[str | ReferenceItem]) -> list[ReferenceItem]:
    items: list[ReferenceItem] = []
    for value in values:
        if isinstance(value, ReferenceItem):
            items.append(value)
        elif value.strip():
            items.append(ReferenceItem(label=value.strip(), source_kind="text"))
    return items


def _empty_analysis() -> ReferenceAnalysis:
    return ReferenceAnalysis(
        negative_constraints=_negative_constraints(),
        summary=(
            "No explicit reference signals were provided; use the product brief and "
            "design contract as the primary source of direction."
        ),
    )


def _negative_constraints(image_analysis: ReferenceImageAnalysis | None = None) -> list[str]:
    constraints = [
        REFERENCE_COPY_CONSTRAINT,
        "Use references only for quality, mood, composition, and interaction signals.",
        "Do not create named product templates from references.",
    ]
    if image_analysis is not None:
        constraints.extend(image_analysis.negative_constraints)
    return _unique(constraints)


def _summary(
    *,
    mood_signals: list[ReferenceSignal],
    composition_signals: list[ReferenceSignal],
    visual_quality_signals: list[ReferenceSignal],
    interaction_signals: list[ReferenceSignal],
    platform_signals: list[ReferenceSignal],
) -> str:
    signal_types = [
        signal.signal_type
        for signals in (
            mood_signals,
            composition_signals,
            visual_quality_signals,
            interaction_signals,
            platform_signals,
        )
        for signal in signals
    ]
    if not signal_types:
        return (
            "References did not contain strong deterministic visual signals; keep "
            "the direction product-specific and avoid copying any source."
        )
    return "Reference metadata suggests: " + ", ".join(_unique(signal_types)) + "."


def _dedupe_signals(signals: list[ReferenceSignal]) -> list[ReferenceSignal]:
    result: list[ReferenceSignal] = []
    seen: set[str] = set()
    for signal in signals:
        if signal.signal_type in seen:
            continue
        result.append(signal)
        seen.add(signal.signal_type)
    return result


def _reference_image_signal_types(image_analysis: ReferenceImageAnalysis | None) -> list[str]:
    if image_analysis is None:
        return []
    signal_types: list[str] = []
    for signals in (
        image_analysis.composition_signals,
        image_analysis.color_signals,
        image_analysis.density_signals,
        image_analysis.platform_signals,
        image_analysis.quality_signals,
    ):
        signal_types.extend(signal.signal_type for signal in signals)
    return _unique(signal_types)


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        result.append(value)
        seen.add(value)
    return result


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()
