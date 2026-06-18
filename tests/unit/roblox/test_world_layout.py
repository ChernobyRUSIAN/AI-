from vuls.roblox import (
    MapZone,
    WorldLayout,
    WorldObject,
    build_roblox_world_layout,
)


def test_obby_world_layout_contains_spawn_checkpoints_platforms_lava_and_finish() -> None:
    layout = build_roblox_world_layout("Сделай Roblox obby карту с лавой и 10 уровнями")

    assert isinstance(layout, WorldLayout)
    assert layout.game_type == "obby"
    object_names = {world_object.name for zone in layout.zones for world_object in zone.objects}
    object_types = {world_object.type for zone in layout.zones for world_object in zone.objects}

    assert {
        "Spawn",
        "Checkpoint 1",
        "Checkpoint 10",
        "Platform 1",
        "Platform 10",
        "Lava Pool",
        "Finish",
    }.issubset(object_names)
    assert {"spawn", "checkpoint", "platform", "lava", "finish"}.issubset(object_types)
    assert len([name for name in object_names if name.startswith("Checkpoint")]) == 10
    assert len([name for name in object_names if name.startswith("Platform")]) == 10


def test_every_world_object_has_required_geometry_and_purpose() -> None:
    layout = build_roblox_world_layout("Сделай Roblox obby карту с лавой и 10 уровнями")

    for zone in layout.zones:
        assert isinstance(zone, MapZone)
        assert zone.name
        assert zone.purpose
        assert zone.objects
        for world_object in zone.objects:
            assert isinstance(world_object, WorldObject)
            assert world_object.name
            assert world_object.type
            assert len(world_object.position) == 3
            assert len(world_object.size) == 3
            assert all(isinstance(value, int | float) for value in world_object.position)
            assert all(value > 0 for value in world_object.size)
            assert world_object.purpose


def test_world_layout_supports_all_roblox_game_types() -> None:
    examples = {
        "obby": "obby с лавой",
        "tycoon": "tycoon где строишь ресторан",
        "simulator": "симулятор прокачки силы",
        "racing": "гонки на машинах",
        "horror": "хоррор в школе",
        "roleplay": "roleplay город",
    }

    for expected_type, prompt in examples.items():
        layout = build_roblox_world_layout(prompt)

        assert layout.game_type == expected_type
        assert layout.zones
        assert any(zone.objects for zone in layout.zones)
