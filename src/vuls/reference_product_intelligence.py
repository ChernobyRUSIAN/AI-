from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from vuls.reference_analysis import ReferenceAnalysis
from vuls.reference_image_intelligence import ReferenceImageAnalysis


class ProductCategory(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    category: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class ProductFeature(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class ProductPattern(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    pattern_name: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class ReferenceProductInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    reference_analysis: ReferenceAnalysis | None = None
    image_analysis: ReferenceImageAnalysis | None = None
    user_intent: str | None = None
    domain: str | None = None
    platform: str | None = None


class ReferenceProductAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    product_type: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    detected_features: list[ProductFeature] = Field(default_factory=list)
    detected_patterns: list[ProductPattern] = Field(default_factory=list)
    suggested_product_structure: list[str] = Field(default_factory=list)
    reasoning: str = Field(min_length=1)


@dataclass(frozen=True)
class ProductTypeProfile:
    product_type: str
    keywords: tuple[str, ...]
    structure: tuple[str, ...]


PRODUCT_TYPE_PROFILES: tuple[ProductTypeProfile, ...] = (
    ProductTypeProfile(
        product_type="SaaS Workspace",
        keywords=(
            "saas",
            "workspace",
            "teamly",
            "documents",
            "docs",
            "team members",
            "billing",
            "settings",
            "workspace platform",
        ),
        structure=(
            "Authentication",
            "Workspace",
            "Dashboard",
            "Documents",
            "Team Members",
            "Billing",
            "Settings",
        ),
    ),
    ProductTypeProfile(
        product_type="CRM",
        keywords=("crm", "customers", "deals", "pipeline", "leads", "reports"),
        structure=("Dashboard", "Customers", "Deals", "Reports", "Settings"),
    ),
    ProductTypeProfile(
        product_type="Learning Platform",
        keywords=(
            "learning",
            "courses",
            "lessons",
            "student",
            "progress",
            "achievements",
        ),
        structure=("Lessons", "Progress", "Achievements", "Profile", "Settings"),
    ),
    ProductTypeProfile(
        product_type="Marketplace",
        keywords=("marketplace", "listings", "seller", "buyer", "orders", "payments"),
        structure=("Browse", "Listings", "Orders", "Payments", "Profile"),
    ),
    ProductTypeProfile(
        product_type="Social Network",
        keywords=("social", "feed", "friends", "followers", "posts", "messages"),
        structure=("Feed", "Profile", "Messages", "Notifications", "Settings"),
    ),
    ProductTypeProfile(
        product_type="Fitness Platform",
        keywords=("fitness", "workout", "trainer", "member", "classes", "progress"),
        structure=("Dashboard", "Workouts", "Progress", "Members", "Settings"),
    ),
    ProductTypeProfile(
        product_type="Trading Platform",
        keywords=("trading", "portfolio", "market", "stocks", "orders", "charts"),
        structure=("Markets", "Portfolio", "Orders", "Analytics", "Settings"),
    ),
    ProductTypeProfile(
        product_type="AI Tool",
        keywords=("ai", "prompt", "chat", "generation", "assistant", "automation"),
        structure=("Workspace", "Prompts", "Generations", "History", "Settings"),
    ),
    ProductTypeProfile(
        product_type="E-commerce",
        keywords=("e-commerce", "ecommerce", "cart", "products", "checkout", "orders"),
        structure=("Catalog", "Product Detail", "Cart", "Checkout", "Profile"),
    ),
    ProductTypeProfile(
        product_type="Dashboard",
        keywords=("dashboard", "analytics", "metrics", "reports", "filters", "kpi"),
        structure=("Dashboard", "Analytics", "Reports", "Search", "Settings"),
    ),
)


FEATURE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "sidebar": ("sidebar", "left navigation", "left nav", "navigation rail"),
    "dashboard": ("dashboard", "overview", "home"),
    "billing": ("billing", "subscription", "invoice", "payment plan"),
    "authentication": ("authentication", "login", "signup", "sign in", "auth"),
    "settings": ("settings", "preferences", "configuration"),
    "team management": ("team", "team members", "members", "roles", "permissions"),
    "analytics": ("analytics", "metrics", "reports", "kpi", "charts"),
    "profile": ("profile", "account", "user profile"),
    "documents": ("documents", "docs", "files", "knowledge base"),
    "search": ("search", "command palette", "filter"),
    "notifications": ("notifications", "alerts", "inbox", "activity"),
}


PATTERN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "left navigation": ("sidebar", "left navigation", "navigation rail"),
    "card layout": ("card", "cards", "kpi", "tiles"),
    "table layout": ("table", "grid", "rows", "pipeline"),
    "workspace structure": ("workspace", "team", "documents", "projects"),
    "onboarding flow": ("onboarding", "signup", "activation", "getting started"),
    "dashboard-first design": ("dashboard", "analytics", "metrics", "overview"),
}


def analyze_reference_product(
    product_input: ReferenceProductInput,
) -> ReferenceProductAnalysis:
    haystack = _product_haystack(product_input)
    if not haystack:
        return _empty_analysis()

    profile, match_count = _detect_product_type(haystack)
    if profile is None:
        return _empty_analysis()

    features = _detect_features(haystack)
    patterns = _detect_patterns(haystack)
    structure = _suggested_structure(
        product_type=profile.product_type,
        base_structure=profile.structure,
        features=features,
    )
    confidence = min(0.95, 0.45 + match_count * 0.08 + len(features) * 0.03)

    return ReferenceProductAnalysis(
        product_type=profile.product_type,
        confidence=confidence,
        detected_features=features,
        detected_patterns=patterns,
        suggested_product_structure=structure,
        reasoning=(
            f"Detected {profile.product_type} from reference product keywords and "
            f"{len(features)} feature signal(s)."
        ),
    )


def load_reference_product_analysis(
    *,
    payload: Mapping[str, Any],
    reference_analysis: ReferenceAnalysis | None = None,
    image_analysis: ReferenceImageAnalysis | None = None,
    user_intent: str | None = None,
    domain: str | None = None,
    platform: str | None = None,
) -> ReferenceProductAnalysis | None:
    existing = payload.get("reference_product_analysis")
    if isinstance(existing, Mapping):
        return ReferenceProductAnalysis.model_validate(dict(existing))
    if reference_analysis is None and isinstance(payload.get("reference_analysis"), Mapping):
        reference_analysis = ReferenceAnalysis.model_validate(
            dict(payload["reference_analysis"])
        )
    if image_analysis is None and isinstance(payload.get("reference_image_analysis"), Mapping):
        image_analysis = ReferenceImageAnalysis.model_validate(
            dict(payload["reference_image_analysis"])
        )
    if image_analysis is None:
        return None

    analysis = analyze_reference_product(
        ReferenceProductInput(
            reference_analysis=reference_analysis,
            image_analysis=image_analysis,
            user_intent=user_intent,
            domain=domain,
            platform=platform,
        )
    )
    return None if analysis.product_type == "Unknown" else analysis


def reference_product_analysis_prompt_items(
    analysis: ReferenceProductAnalysis,
) -> list[str]:
    items = [
        (
            "Reference Product Intelligence: "
            f"product_type={analysis.product_type}; "
            f"confidence={analysis.confidence:.2f}; "
            f"reasoning={analysis.reasoning}"
        )
    ]
    if analysis.detected_features:
        items.append(
            "Reference product features: "
            + ", ".join(feature.name for feature in analysis.detected_features)
        )
    if analysis.detected_patterns:
        items.append(
            "Reference product patterns: "
            + ", ".join(pattern.pattern_name for pattern in analysis.detected_patterns)
        )
    if analysis.suggested_product_structure:
        items.append(
            "Suggested product structure: "
            + " -> ".join(analysis.suggested_product_structure)
        )
    return items


def _detect_product_type(
    haystack: str,
) -> tuple[ProductTypeProfile | None, int]:
    best_profile: ProductTypeProfile | None = None
    best_score = 0
    for profile in PRODUCT_TYPE_PROFILES:
        score = sum(1 for keyword in profile.keywords if _has_keyword(haystack, keyword))
        if score > best_score:
            best_profile = profile
            best_score = score
    return best_profile, best_score


def _detect_features(haystack: str) -> list[ProductFeature]:
    features: list[ProductFeature] = []
    for name, keywords in FEATURE_KEYWORDS.items():
        matches = sum(1 for keyword in keywords if _has_keyword(haystack, keyword))
        if matches == 0:
            continue
        features.append(
            ProductFeature(
                name=name,
                confidence=min(0.95, 0.58 + matches * 0.09),
            )
        )
    return features


def _detect_patterns(haystack: str) -> list[ProductPattern]:
    patterns: list[ProductPattern] = []
    for pattern_name, keywords in PATTERN_KEYWORDS.items():
        if not any(_has_keyword(haystack, keyword) for keyword in keywords):
            continue
        patterns.append(
            ProductPattern(
                pattern_name=pattern_name,
                reason=f"Reference signals mention {pattern_name} cues.",
            )
        )
    return patterns


def _suggested_structure(
    *,
    product_type: str,
    base_structure: tuple[str, ...],
    features: list[ProductFeature],
) -> list[str]:
    structure = list(base_structure)
    feature_names = {feature.name for feature in features}
    additions = {
        "documents": "Documents",
        "team management": "Team Members",
        "billing": "Billing",
        "settings": "Settings",
        "profile": "Profile",
        "search": "Search",
        "notifications": "Notifications",
        "analytics": "Analytics",
    }
    if product_type == "CRM":
        return structure
    for feature_name, section in additions.items():
        if feature_name in feature_names and section not in structure:
            structure.append(section)
    return _unique(structure)


def _product_haystack(product_input: ReferenceProductInput) -> str:
    parts = [
        product_input.user_intent or "",
        product_input.domain or "",
        product_input.platform or "",
    ]
    if product_input.reference_analysis is not None:
        parts.append(product_input.reference_analysis.summary)
        for signals in (
            product_input.reference_analysis.mood_signals,
            product_input.reference_analysis.composition_signals,
            product_input.reference_analysis.visual_quality_signals,
            product_input.reference_analysis.interaction_signals,
            product_input.reference_analysis.platform_signals,
        ):
            parts.extend(_signal_parts(signal) for signal in signals)
    if product_input.image_analysis is not None:
        parts.append(product_input.image_analysis.summary)
        for image_signals in (
            product_input.image_analysis.composition_signals,
            product_input.image_analysis.color_signals,
            product_input.image_analysis.density_signals,
            product_input.image_analysis.platform_signals,
            product_input.image_analysis.quality_signals,
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


def _empty_analysis() -> ReferenceProductAnalysis:
    return ReferenceProductAnalysis(
        product_type="Unknown",
        confidence=0.0,
        reasoning=(
            "No reference product signals were available; keep using text Product "
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


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        result.append(value)
        seen.add(key)
    return result
