from vuls.roblox import (
    RobloxBuildPackage,
    RobloxGamePlan,
    build_roblox_game_plan,
    build_roblox_package,
    detect_roblox_game_type,
)


def test_detects_obby_from_russian_lava_prompt() -> None:
    assert detect_roblox_game_type("Сделай Roblox obby карту с лавой и 10 уровнями") == "obby"


def test_detects_tycoon() -> None:
    assert detect_roblox_game_type("tycoon где строишь ресторан") == "tycoon"


def test_detects_simulator() -> None:
    assert detect_roblox_game_type("симулятор прокачки силы") == "simulator"


def test_detects_racing() -> None:
    assert detect_roblox_game_type("гонки на машинах") == "racing"


def test_detects_horror() -> None:
    assert detect_roblox_game_type("хоррор в школе") == "horror"


def test_detects_roleplay() -> None:
    assert detect_roblox_game_type("roleplay город") == "roleplay"


def test_unknown_prompt_falls_back_to_obby() -> None:
    assert detect_roblox_game_type("сделай веселую карту") == "obby"


def test_obby_plan_contains_required_map_structure() -> None:
    plan = build_roblox_game_plan("Сделай Roblox obby карту с лавой и 10 уровнями")

    assert isinstance(plan, RobloxGamePlan)
    assert plan.game_type == "obby"
    assert "10" in " ".join([plan.title, plan.core_loop, *plan.map_sections])
    assert any("Checkpoint" in section for section in plan.map_sections)
    assert any("Lava" in section for section in plan.map_sections)
    assert any("Finish" in section for section in plan.map_sections)
    assert any("Reward" in section for section in plan.map_sections)
    assert any("checkpoint" in item.casefold() for item in plan.mechanics)
    assert any("lava" in item.casefold() for item in plan.objects)
    assert any("finish" in item.casefold() for item in plan.testing_steps)


def test_package_includes_manual_roblox_studio_instructions() -> None:
    package = build_roblox_package("Сделай Roblox obby карту с лавой и 10 уровнями")

    assert isinstance(package, RobloxBuildPackage)
    instructions = " ".join(package.studio_instructions)
    assert "Open Roblox Studio" in instructions
    assert "Create Baseplate" in instructions
    assert "Add required Parts/Models" in instructions
    assert "Add Script or LocalScript" in instructions
    assert "Paste generated Lua" in instructions
    assert "Press Play" in instructions
    assert "Test checkpoints/damage/rewards" in instructions
    assert package.plan.game_type == "obby"
    assert package.scripts
