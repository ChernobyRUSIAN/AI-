from vuls.reference_image_intelligence import (
    ReferenceImageInput,
    ReferenceImageItem,
    analyze_reference_images,
    reference_image_analysis_prompt_items,
)


def test_empty_image_input_returns_safe_default_analysis() -> None:
    analysis = analyze_reference_images(ReferenceImageInput())

    assert analysis.summary
    assert analysis.composition_signals == []
    assert analysis.color_signals == []
    assert analysis.density_signals == []
    assert analysis.platform_signals == []
    assert analysis.quality_signals == []
    assert any("not copy targets" in item.lower() for item in analysis.negative_constraints)


def test_portrait_image_metadata_creates_mobile_portrait_signal() -> None:
    analysis = analyze_reference_images(
        ReferenceImageInput(
            images=[
                ReferenceImageItem(
                    filename="reward-mobile.webp",
                    mime_type="image/webp",
                    width=390,
                    height=844,
                    size_bytes=120_000,
                    caption="Mobile reward app screenshot",
                    tags=["mobile"],
                )
            ]
        )
    )

    assert "mobile_portrait_reference" in _signal_types(analysis)


def test_wide_image_metadata_creates_wide_hero_signal() -> None:
    analysis = analyze_reference_images(
        ReferenceImageInput(
            images=[
                ReferenceImageItem(
                    filename="premium-travel-hero.png",
                    mime_type="image/png",
                    width=1600,
                    height=700,
                    size_bytes=320_000,
                    caption="Wide premium travel hero screenshot",
                    tags=["travel", "hero"],
                )
            ]
        )
    )

    assert "wide_hero_reference" in _signal_types(analysis)
    assert "strong_focal_object" in _signal_types(analysis)


def test_drone_control_metadata_creates_technical_control_signal() -> None:
    analysis = analyze_reference_images(
        ReferenceImageInput(
            images=[
                ReferenceImageItem(
                    filename="dark-drone-control-dashboard.webp",
                    mime_type="image/webp",
                    width=390,
                    height=844,
                    size_bytes=180_000,
                    caption="Dark telemetry, radar, flight control interface.",
                    tags=["drone", "control", "terminal"],
                )
            ]
        )
    )

    assert "technical_control_reference" in _signal_types(analysis)
    assert "dark_interface_reference" in _signal_types(analysis)
    assert "bright_clean_interface_reference" not in _signal_types(analysis)


def test_glass_premium_caption_creates_depth_and_glass_signals() -> None:
    analysis = analyze_reference_images(
        ReferenceImageInput(
            images=[
                ReferenceImageItem(
                    filename="premium-glow-ui.png",
                    mime_type="image/png",
                    width=1200,
                    height=900,
                    size_bytes=250_000,
                    caption="Glass blur glow premium layered cards.",
                    tags=["glass", "premium", "glow"],
                )
            ]
        )
    )

    assert {"premium_depth_reference", "glass_layering_reference"} <= _signal_types(analysis)


def test_gamified_reference_forbids_copying_mascots_and_brand_identity() -> None:
    analysis = analyze_reference_images(
        ReferenceImageInput(
            images=[
                ReferenceImageItem(
                    filename="duolingo-like-reward.webp",
                    mime_type="image/webp",
                    width=390,
                    height=844,
                    size_bytes=160_000,
                    caption="Duolingo-like mascot streak reward app screenshot.",
                    tags=["mascot", "reward", "game"],
                )
            ]
        )
    )

    prompt = "\n".join(reference_image_analysis_prompt_items(analysis)).lower()

    assert "gamified_character_reference" in _signal_types(analysis)
    assert "do not copy logos" in prompt
    assert "mascots" in prompt
    assert "brand assets" in prompt
    assert "recognizable identity" in prompt


def test_dashboard_metadata_creates_desktop_and_density_signals() -> None:
    analysis = analyze_reference_images(
        ReferenceImageInput(
            images=[
                ReferenceImageItem(
                    filename="crm-analytics-dashboard.png",
                    mime_type="image/png",
                    width=1440,
                    height=1024,
                    size_bytes=400_000,
                    caption="CRM analytics table dashboard with many cards.",
                    tags=["dashboard", "analytics", "table"],
                )
            ]
        )
    )

    assert "desktop_dashboard_reference" in _signal_types(analysis)
    assert "high_density_dashboard" in _signal_types(analysis)


def test_medical_metadata_creates_medical_clean_signal() -> None:
    analysis = analyze_reference_images(
        ReferenceImageInput(
            images=[
                ReferenceImageItem(
                    filename="dentistry-clinic-dashboard.png",
                    mime_type="image/png",
                    width=1280,
                    height=900,
                    size_bytes=280_000,
                    caption="Clean medical clinic health dashboard.",
                    tags=["dentistry", "medical", "clinic"],
                )
            ]
        )
    )

    assert "medical_clean_reference" in _signal_types(analysis)


def _signal_types(analysis: object) -> set[str]:
    signals = []
    for field in (
        "composition_signals",
        "color_signals",
        "density_signals",
        "platform_signals",
        "quality_signals",
    ):
        signals.extend(getattr(analysis, field))
    return {signal.signal_type for signal in signals}
