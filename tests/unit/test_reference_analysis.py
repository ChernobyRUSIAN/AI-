from vuls.reference_analysis import (
    ReferenceInput,
    ReferenceItem,
    analyze_references,
    reference_analysis_prompt_items,
)
from vuls.reference_image_intelligence import (
    ReferenceImageInput,
    ReferenceImageItem,
    analyze_reference_images,
)


def test_empty_references_return_safe_default_analysis() -> None:
    analysis = analyze_references(
        ReferenceInput(
            domain="fitness",
            user_intent="Create an app for a fitness club",
            platform="mobile",
        )
    )

    assert analysis.summary
    assert analysis.mood_signals == []
    assert analysis.composition_signals == []
    assert analysis.visual_quality_signals == []
    assert analysis.interaction_signals == []
    assert analysis.platform_signals == []
    assert any("inspiration signals" in item.lower() for item in analysis.negative_constraints)


def test_fitness_gamified_reference_becomes_reward_signal_not_template() -> None:
    analysis = analyze_references(
        ReferenceInput(
            domain="fitness",
            user_intent="Fitness club member motivation app",
            references=[
                ReferenceItem(
                    label="Gamified learning app",
                    description="Streaks, celebrations, daily goals, progress rewards.",
                    source_kind="product_name",
                    tags=["streak", "reward", "learning"],
                )
            ],
            platform="mobile",
        )
    )

    assert _signal_types(analysis) >= {"gamified_reward_loop"}

    prompt = "\n".join(reference_analysis_prompt_items(analysis)).lower()
    assert "inspiration signals, not templates" in prompt
    assert "gamified learning app template" not in prompt
    assert "do not copy layouts" in prompt
    assert "brand assets" in prompt
    assert "proprietary ui" in prompt


def test_user_intent_reference_language_is_analyzed_without_items() -> None:
    analysis = analyze_references(
        ReferenceInput(
            domain="fitness",
            user_intent="Create a fitness motivation app inspired by Duolingo streaks.",
            platform="mobile",
        )
    )

    assert "gamified_reward_loop" in _signal_types(analysis)


def test_travel_premium_reference_becomes_depth_and_hero_signal() -> None:
    analysis = analyze_references(
        ReferenceInput(
            domain="travel",
            user_intent="AI-powered travel concierge",
            references=[
                ReferenceItem(
                    label="Premium travel assistant",
                    description="Immersive destination hero, layered cards, booking action.",
                    source_kind="screenshot",
                    tags=["premium", "hero", "glass"],
                )
            ],
            platform="mobile",
        )
    )

    assert {"premium_depth", "strong_hero_object"} <= _signal_types(analysis)


def test_drone_technical_reference_becomes_dark_control_signal() -> None:
    analysis = analyze_references(
        ReferenceInput(
            domain="drone operations",
            user_intent="Drone fleet control center",
            references=[
                ReferenceItem(
                    label="Technical operator UI",
                    description="Dark telemetry, flight tracking, control mode, signal grid.",
                    source_kind="screenshot",
                    tags=["drone", "technical", "telemetry"],
                )
            ],
            platform="mobile",
        )
    )

    assert [signal.signal_type for signal in analysis.mood_signals][0] == (
        "dark_technical_control"
    )
    assert "calm_operational_clarity" not in [
        signal.signal_type for signal in analysis.mood_signals
    ] or analysis.mood_signals[0].signal_type == "dark_technical_control"
    assert "map_first_spatial_context" not in [
        signal.signal_type for signal in analysis.composition_signals
    ]


def test_medical_reference_becomes_clean_medical_trust_signal() -> None:
    analysis = analyze_references(
        ReferenceInput(
            domain="medical",
            user_intent="Patient monitoring workspace",
            references=[
                ReferenceItem(
                    label="Health dashboard",
                    description="Clean clinical data, trust, risk cards, patient monitoring.",
                    source_kind="moodboard",
                    tags=["medical", "clinical", "trust"],
                )
            ],
            platform="web",
        )
    )

    assert "clean_medical_trust" in _signal_types(analysis)


def test_map_logistics_reference_becomes_spatial_context_signal() -> None:
    analysis = analyze_references(
        ReferenceInput(
            domain="logistics",
            user_intent="Fleet delivery operations",
            references=[
                ReferenceItem(
                    label="Map operations UI",
                    description="Route map, delivery progress, vehicle location, dispatch panels.",
                    source_kind="screenshot",
                    tags=["map", "route", "fleet"],
                )
            ],
            platform="web",
        )
    )

    assert "map_first_spatial_context" in _signal_types(analysis)


def test_bottom_navigation_reference_is_interaction_signal() -> None:
    analysis = analyze_references(
        ReferenceInput(
            domain="mobile productivity",
            user_intent="Task app with thumb-first controls",
            references=[
                ReferenceItem(
                    label="Mobile app navigation",
                    description="Bottom navigation, one thumb actions, mobile tab bar.",
                    source_kind="screenshot",
                    tags=["bottom nav", "thumb"],
                )
            ],
            platform="mobile",
        )
    )

    assert "mobile_first_bottom_navigation" in [
        signal.signal_type for signal in analysis.interaction_signals
    ]
    assert "mobile_first_bottom_navigation" not in [
        signal.signal_type for signal in analysis.platform_signals
    ]


def test_image_analysis_signals_are_mapped_into_reference_analysis() -> None:
    image_analysis = analyze_reference_images(
        ReferenceImageInput(
            images=[
                ReferenceImageItem(
                    filename="duolingo-like-reward.webp",
                    mime_type="image/webp",
                    width=390,
                    height=844,
                    size_bytes=160_000,
                    caption="Mascot streak reward mobile screen.",
                    tags=["reward", "mascot", "streak"],
                )
            ]
        )
    )

    analysis = analyze_references(
        ReferenceInput(
            domain="fitness",
            user_intent="Fitness motivation app",
            platform="mobile",
            image_analysis=image_analysis,
        )
    )

    assert "gamified_reward_loop" in [
        signal.signal_type for signal in analysis.interaction_signals
    ]
    assert "mobile_first_bottom_navigation" in [
        signal.signal_type for signal in analysis.interaction_signals
    ]
    assert "strong_hero_object" in [
        signal.signal_type for signal in analysis.composition_signals
    ]
    assert any("mascots" in item.lower() for item in analysis.negative_constraints)


def _signal_types(analysis: object) -> set[str]:
    signals = []
    for field in (
        "mood_signals",
        "composition_signals",
        "visual_quality_signals",
        "interaction_signals",
        "platform_signals",
    ):
        signals.extend(getattr(analysis, field))
    return {signal.signal_type for signal in signals}
