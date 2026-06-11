from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ReferenceImageItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    filename: str = ""
    mime_type: str = ""
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    size_bytes: int | None = Field(default=None, ge=0)
    caption: str = ""
    tags: list[str] = Field(default_factory=list)
    user_declared_style: str | None = None
    extracted_palette: list[str] = Field(default_factory=list)


class ReferenceImageInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    images: list[ReferenceImageItem] = Field(default_factory=list)
    domain: str | None = None
    user_intent: str | None = None
    platform: str | None = None


class ReferenceImageSignal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    signal_type: str = Field(min_length=1)
    value: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)


class ImageCompositionSignal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    signals: list[ReferenceImageSignal] = Field(default_factory=list)


class ImageQualitySignal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    signals: list[ReferenceImageSignal] = Field(default_factory=list)


class ImageConstraint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    negative_constraints: list[str] = Field(default_factory=list)


class ReferenceImageAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    composition_signals: list[ReferenceImageSignal] = Field(default_factory=list)
    color_signals: list[ReferenceImageSignal] = Field(default_factory=list)
    density_signals: list[ReferenceImageSignal] = Field(default_factory=list)
    platform_signals: list[ReferenceImageSignal] = Field(default_factory=list)
    quality_signals: list[ReferenceImageSignal] = Field(default_factory=list)
    negative_constraints: list[str] = Field(default_factory=list)
    summary: str = Field(min_length=1)


IMAGE_COPY_CONSTRAINT = (
    "Image references are visual quality signals, not copy targets. Do not copy logos, "
    "brand assets, mascots, characters, proprietary layouts, or recognizable identity."
)


def analyze_reference_images(image_input: ReferenceImageInput) -> ReferenceImageAnalysis:
    if not image_input.images:
        return _empty_analysis()

    composition_signals: list[ReferenceImageSignal] = []
    color_signals: list[ReferenceImageSignal] = []
    density_signals: list[ReferenceImageSignal] = []
    platform_signals: list[ReferenceImageSignal] = []
    quality_signals: list[ReferenceImageSignal] = []

    for image in image_input.images:
        text = _image_haystack(image, image_input)
        _append_aspect_ratio_signals(
            image=image,
            composition_signals=composition_signals,
            platform_signals=platform_signals,
        )
        _append_if_match(
            target=quality_signals,
            text=text,
            signal_type="technical_control_reference",
            keywords=("drone", "radar", "control", "terminal", "telemetry", "flight"),
            value="Use technical control signals as abstract command-center direction.",
            rationale="Image metadata mentions technical control, telemetry, or operator UI.",
        )
        _append_if_match(
            target=color_signals,
            text=text,
            signal_type="dark_interface_reference",
            keywords=("dark", "terminal", "radar", "night", "black"),
            value="Consider a dark interface direction when it supports operational focus.",
            rationale="Image metadata points to a dark technical or low-light interface.",
        )
        _append_if_match(
            target=color_signals,
            text=text,
            signal_type="bright_clean_interface_reference",
            keywords=("bright", "clean", "white", "minimal", "light"),
            value="Consider a bright clean interface direction with restrained contrast.",
            rationale="Image metadata points to clean light UI surfaces.",
        )
        _append_if_match(
            target=quality_signals,
            text=text,
            signal_type="premium_depth_reference",
            keywords=("glass", "blur", "glow", "premium", "depth", "cinematic", "luxury"),
            value="Raise the visual quality bar with depth, polish, and careful layering.",
            rationale="Image metadata mentions premium depth, glow, or polished layering.",
        )
        _append_if_match(
            target=quality_signals,
            text=text,
            signal_type="glass_layering_reference",
            keywords=("glass", "blur", "frosted", "translucent", "layered", "layers"),
            value="Use restrained glass-like layering only as an abstract depth signal.",
            rationale="Image metadata mentions glass, blur, or translucent layers.",
        )
        _append_if_match(
            target=composition_signals,
            text=text,
            signal_type="map_or_spatial_reference",
            keywords=("map", "geo", "route", "logistics", "location", "dispatch", "spatial"),
            value="Use spatial context where maps, routes, or location drive decisions.",
            rationale="Image metadata mentions map, geography, route, or logistics context.",
        )
        _append_if_match(
            target=quality_signals,
            text=text,
            signal_type="gamified_character_reference",
            keywords=("duolingo", "streak", "mascot", "reward", "game", "character"),
            value="Use gamified motivation signals without copying characters or mascots.",
            rationale="Image metadata mentions reward loops, streaks, game UI, or mascots.",
        )
        _append_if_match(
            target=quality_signals,
            text=text,
            signal_type="medical_clean_reference",
            keywords=("medical", "health", "clinic", "dentistry", "dental", "patient"),
            value="Use clean medical trust as an abstract visual quality direction.",
            rationale="Image metadata mentions clinical, health, dental, or patient context.",
        )
        _append_if_match(
            target=composition_signals,
            text=text,
            signal_type="desktop_dashboard_reference",
            keywords=("dashboard", "analytics", "crm", "table", "admin", "workspace"),
            value="Use dashboard layout signals for dense operational workspaces.",
            rationale="Image metadata mentions dashboard, analytics, CRM, or table UI.",
        )
        _append_if_match(
            target=density_signals,
            text=text,
            signal_type="high_density_dashboard",
            keywords=("dashboard", "analytics", "crm", "table", "metrics", "many cards"),
            value="Use high-density modules when the product needs fast operational scanning.",
            rationale="Image metadata points to dashboards, tables, metrics, or dense cards.",
        )
        _append_if_match(
            target=density_signals,
            text=text,
            signal_type="low_density_landing",
            keywords=("landing", "hero", "travel", "marketing", "showcase"),
            value="Use lower-density hero-led composition when the reference is landing-like.",
            rationale="Image metadata mentions landing, hero, travel, or showcase composition.",
        )
        _append_if_match(
            target=composition_signals,
            text=text,
            signal_type="strong_focal_object",
            keywords=("hero", "travel", "object", "mascot", "character", "device", "product"),
            value="Use a strong product-specific focal object without copying the image.",
            rationale="Image metadata points to a central object, hero, device, or character.",
        )

    return ReferenceImageAnalysis(
        composition_signals=_dedupe_signals(composition_signals),
        color_signals=_dedupe_signals(color_signals),
        density_signals=_dedupe_signals(density_signals),
        platform_signals=_dedupe_signals(platform_signals),
        quality_signals=_dedupe_signals(quality_signals),
        negative_constraints=_negative_constraints(),
        summary=_summary(
            composition_signals=composition_signals,
            color_signals=color_signals,
            density_signals=density_signals,
            platform_signals=platform_signals,
            quality_signals=quality_signals,
        ),
    )


def load_reference_image_analysis(
    *,
    payload: Mapping[str, Any],
) -> ReferenceImageAnalysis | None:
    existing = payload.get("reference_image_analysis")
    if isinstance(existing, Mapping):
        return ReferenceImageAnalysis.model_validate(dict(existing))
    return None


def reference_image_analysis_prompt_items(analysis: ReferenceImageAnalysis) -> list[str]:
    items = [f"Reference Image Intelligence: {analysis.summary}"]
    for label, signals in (
        ("Image composition signals", analysis.composition_signals),
        ("Image color signals", analysis.color_signals),
        ("Image density signals", analysis.density_signals),
        ("Image platform signals", analysis.platform_signals),
        ("Image quality signals", analysis.quality_signals),
    ):
        if signals:
            items.append(
                f"{label}: "
                + "; ".join(
                    f"{signal.signal_type}={signal.value}" for signal in signals
                )
            )
    items.append("Image reference constraints: " + " ".join(analysis.negative_constraints))
    return items


def _append_aspect_ratio_signals(
    *,
    image: ReferenceImageItem,
    composition_signals: list[ReferenceImageSignal],
    platform_signals: list[ReferenceImageSignal],
) -> None:
    if image.width is None or image.height is None:
        return
    ratio = image.width / image.height
    if ratio <= 0.72:
        platform_signals.append(
            ReferenceImageSignal(
                signal_type="mobile_portrait_reference",
                value="Use mobile portrait ergonomics and thumb-reachable hierarchy.",
                confidence=0.9,
                rationale="Image metadata aspect ratio is portrait.",
            )
        )
        return
    if ratio >= 1.65:
        composition_signals.append(
            ReferenceImageSignal(
                signal_type="wide_hero_reference",
                value="Use wide hero composition only as an abstract layout signal.",
                confidence=0.88,
                rationale="Image metadata aspect ratio is wide.",
            )
        )


def _append_if_match(
    *,
    target: list[ReferenceImageSignal],
    text: str,
    signal_type: str,
    keywords: tuple[str, ...],
    value: str,
    rationale: str,
) -> None:
    matches = sum(1 for keyword in keywords if _has_keyword(text, keyword))
    if matches == 0:
        return
    confidence = min(0.95, 0.58 + matches * 0.08)
    target.append(
        ReferenceImageSignal(
            signal_type=signal_type,
            value=value,
            confidence=confidence,
            rationale=rationale,
        )
    )


def _image_haystack(image: ReferenceImageItem, image_input: ReferenceImageInput) -> str:
    return _normalized_text(
        " ".join(
            [
                image.filename,
                image.mime_type,
                image.caption,
                image.user_declared_style or "",
                " ".join(image.tags),
                " ".join(image.extracted_palette),
                image_input.domain or "",
                image_input.user_intent or "",
                image_input.platform or "",
            ]
        )
    )


def _has_keyword(text: str, keyword: str) -> bool:
    normalized_keyword = _normalized_text(keyword)
    if " " in normalized_keyword:
        return normalized_keyword in text
    return re.search(rf"\b{re.escape(normalized_keyword)}\b", text) is not None


def _empty_analysis() -> ReferenceImageAnalysis:
    return ReferenceImageAnalysis(
        negative_constraints=_negative_constraints(),
        summary=(
            "No image reference metadata was provided; use text references and product "
            "intelligence as the primary direction."
        ),
    )


def _negative_constraints() -> list[str]:
    return [
        IMAGE_COPY_CONSTRAINT,
        "Use image references only for visual quality, composition, density, and platform signals.",
        "Do not use screenshots as pixel-perfect clone targets.",
    ]


def _summary(
    *,
    composition_signals: list[ReferenceImageSignal],
    color_signals: list[ReferenceImageSignal],
    density_signals: list[ReferenceImageSignal],
    platform_signals: list[ReferenceImageSignal],
    quality_signals: list[ReferenceImageSignal],
) -> str:
    signal_types = [
        signal.signal_type
        for signals in (
            composition_signals,
            color_signals,
            density_signals,
            platform_signals,
            quality_signals,
        )
        for signal in signals
    ]
    if not signal_types:
        return (
            "Image metadata did not contain strong deterministic visual signals; avoid "
            "copying the source and rely on product context."
        )
    return "Image metadata suggests: " + ", ".join(_unique(signal_types)) + "."


def _dedupe_signals(signals: list[ReferenceImageSignal]) -> list[ReferenceImageSignal]:
    result: list[ReferenceImageSignal] = []
    seen: set[str] = set()
    for signal in signals:
        if signal.signal_type in seen:
            continue
        result.append(signal)
        seen.add(signal.signal_type)
    return result


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
