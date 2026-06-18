from vuls.roblox import (
    build_roblox_game_plan,
    generate_roblox_lua_scripts,
)

UNSAFE_LUA_PATTERNS = (
    "HttpService",
    "require(",
    "game:HttpGet",
    "loadstring",
    "TeleportService",
    "http://",
    "https://",
)


def test_obby_generates_checkpoint_lava_and_finish_scripts() -> None:
    scripts = generate_roblox_lua_scripts(
        build_roblox_game_plan("Сделай Roblox obby карту с лавой и 10 уровнями")
    )
    script_names = {script.name for script in scripts}

    assert {
        "Checkpoint Script",
        "Lava Damage Script",
        "Finish Reward Script",
    }.issubset(script_names)


def test_tycoon_generates_cash_button_and_income_loop_scripts() -> None:
    scripts = generate_roblox_lua_scripts(build_roblox_game_plan("tycoon где строишь ресторан"))
    script_names = {script.name for script in scripts}

    assert {"Cash Button Script", "Income Loop Script"}.issubset(script_names)


def test_simulator_generates_strength_currency_script() -> None:
    scripts = generate_roblox_lua_scripts(build_roblox_game_plan("симулятор прокачки силы"))

    assert any(script.name == "Strength Currency Script" for script in scripts)


def test_racing_generates_checkpoint_lap_script() -> None:
    scripts = generate_roblox_lua_scripts(build_roblox_game_plan("гонки на машинах"))

    assert any(script.name == "Checkpoint Lap Script" for script in scripts)


def test_horror_generates_jump_scare_trigger_script() -> None:
    scripts = generate_roblox_lua_scripts(build_roblox_game_plan("хоррор в школе"))

    assert any(script.name == "Jump Scare Trigger Script" for script in scripts)


def test_roleplay_generates_team_job_assignment_script() -> None:
    scripts = generate_roblox_lua_scripts(build_roblox_game_plan("roleplay город"))

    assert any(script.name == "Team Job Assignment Script" for script in scripts)


def test_every_script_has_complete_metadata_and_code() -> None:
    prompts = [
        "Сделай Roblox obby карту с лавой и 10 уровнями",
        "tycoon где строишь ресторан",
        "симулятор прокачки силы",
        "гонки на машинах",
        "хоррор в школе",
        "roleplay город",
    ]

    for prompt in prompts:
        scripts = generate_roblox_lua_scripts(build_roblox_game_plan(prompt))
        assert scripts
        for script in scripts:
            assert script.name
            assert script.purpose
            assert script.place_in_studio
            assert script.code
            assert "-- Where to put it:" in script.code
            assert "-- Expected object:" in script.code
            assert "-- How to test:" in script.code


def test_scripts_do_not_contain_unsafe_http_or_module_loading_patterns() -> None:
    prompts = [
        "Сделай Roblox obby карту с лавой и 10 уровнями",
        "tycoon где строишь ресторан",
        "симулятор прокачки силы",
        "гонки на машинах",
        "хоррор в школе",
        "roleplay город",
    ]

    all_code = "\n".join(
        script.code
        for prompt in prompts
        for script in generate_roblox_lua_scripts(build_roblox_game_plan(prompt))
    )

    for pattern in UNSAFE_LUA_PATTERNS:
        assert pattern not in all_code
