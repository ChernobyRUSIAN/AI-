from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from vuls.roblox.game_intelligence import RobloxGameType, detect_roblox_game_type

Vector3 = tuple[float, float, float]


class WorldObject(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    position: Vector3
    size: Vector3
    purpose: str = Field(min_length=1)


class MapZone(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    objects: list[WorldObject] = Field(min_length=1)


class WorldLayout(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str = Field(min_length=1)
    game_type: RobloxGameType
    zones: list[MapZone] = Field(min_length=1)


def build_roblox_world_layout(user_idea: str) -> WorldLayout:
    game_type = detect_roblox_game_type(user_idea)
    if game_type == "tycoon":
        return _tycoon_layout()
    if game_type == "simulator":
        return _simulator_layout()
    if game_type == "racing":
        return _racing_layout()
    if game_type == "horror":
        return _horror_layout()
    if game_type == "roleplay":
        return _roleplay_layout()
    return _obby_layout(level_count=_level_count(user_idea) or 6)


def _obby_layout(*, level_count: int) -> WorldLayout:
    clamped_level_count = max(1, min(level_count, 20))
    platforms = [
        WorldObject(
            name=f"Platform {index}",
            type="platform",
            position=(0.0, 2.0, float(index * 24)),
            size=(16.0, 1.0, 12.0),
            purpose=f"Main landing platform for obby level {index}.",
        )
        for index in range(1, clamped_level_count + 1)
    ]
    checkpoints = [
        WorldObject(
            name=f"Checkpoint {index}",
            type="checkpoint",
            position=(0.0, 3.0, float(index * 24 - 8)),
            size=(10.0, 1.0, 2.0),
            purpose=f"Respawn checkpoint before obby level {index}.",
        )
        for index in range(1, clamped_level_count + 1)
    ]
    return WorldLayout(
        title=f"{clamped_level_count}-Level Lava Obby Layout",
        game_type="obby",
        zones=[
            MapZone(
                name="Spawn Zone",
                purpose="Start the player safely before the first obstacle.",
                objects=[
                    WorldObject(
                        name="Spawn",
                        type="spawn",
                        position=(0.0, 4.0, 0.0),
                        size=(12.0, 1.0, 12.0),
                        purpose="Player spawn and tutorial start point.",
                    )
                ],
            ),
            MapZone(
                name="Obstacle Course",
                purpose="Place checkpoints, platforms, and lava hazards in a readable path.",
                objects=[
                    *checkpoints,
                    *platforms,
                    WorldObject(
                        name="Lava Pool",
                        type="lava",
                        position=(0.0, 0.0, float(clamped_level_count * 12)),
                        size=(24.0, 1.0, float(clamped_level_count * 28)),
                        purpose="Damage hazard below the obby route.",
                    ),
                ],
            ),
            MapZone(
                name="Finish Zone",
                purpose="End the run and trigger the reward script.",
                objects=[
                    WorldObject(
                        name="Finish",
                        type="finish",
                        position=(0.0, 3.0, float(clamped_level_count * 24 + 16)),
                        size=(18.0, 1.0, 8.0),
                        purpose="Final touch target for completing the obby.",
                    )
                ],
            ),
        ],
    )


def _tycoon_layout() -> WorldLayout:
    return WorldLayout(
        title="Tycoon Layout",
        game_type="tycoon",
        zones=[
            MapZone(
                name="Base Zone",
                purpose="Give the player a buildable base and first money loop.",
                objects=[
                    _object("Base", "base", (0, 1, 0), (48, 1, 48), "Player tycoon base."),
                    _object("Cash Button", "button", (-12, 2, 8), (6, 1, 6), "Buy first upgrade."),
                    _object("Dropper", "dropper", (8, 4, 8), (8, 8, 8), "Generate income."),
                    _object(
                        "Upgrade Pad",
                        "upgrade",
                        (16, 2, 8),
                        (6, 1, 6),
                        "Unlock better income.",
                    ),
                ],
            )
        ],
    )


def _simulator_layout() -> WorldLayout:
    return WorldLayout(
        title="Simulator Layout",
        game_type="simulator",
        zones=[
            MapZone(
                name="Training Zone",
                purpose="Place training, currency, upgrades, and rewards close together.",
                objects=[
                    _object("Spawn", "spawn", (0, 3, 0), (10, 1, 10), "Player start point."),
                    _object("Training Part", "training", (0, 2, 16), (16, 1, 16), "Gain strength."),
                    _object(
                        "Currency Board",
                        "display",
                        (-14, 6, 16),
                        (8, 10, 1),
                        "Show currency.",
                    ),
                    _object("Upgrade Shop", "shop", (18, 2, 16), (14, 1, 10), "Buy upgrades."),
                    _object("Pet Area", "reward", (0, 2, 34), (18, 1, 12), "Show pets or items."),
                ],
            )
        ],
    )


def _racing_layout() -> WorldLayout:
    return WorldLayout(
        title="Racing Layout",
        game_type="racing",
        zones=[
            MapZone(
                name="Track Zone",
                purpose="Create a simple loop with ordered checkpoints and finish line.",
                objects=[
                    _object("Spawn", "spawn", (0, 3, 0), (12, 1, 12), "Driver spawn."),
                    _object("Track", "track", (0, 1, 40), (60, 1, 120), "Race route."),
                    _object("Checkpoint A", "checkpoint", (0, 2, 20), (18, 1, 4), "Lap progress."),
                    _object("Checkpoint B", "checkpoint", (18, 2, 60), (4, 1, 18), "Lap progress."),
                    _object(
                        "Checkpoint C",
                        "checkpoint",
                        (-18, 2, 60),
                        (4, 1, 18),
                        "Lap progress.",
                    ),
                    _object("Finish Line", "finish", (0, 2, 100), (24, 1, 4), "Complete lap."),
                ],
            )
        ],
    )


def _horror_layout() -> WorldLayout:
    return WorldLayout(
        title="Horror Layout",
        game_type="horror",
        zones=[
            MapZone(
                name="School Escape Zone",
                purpose="Guide the player from spawn through scares to an escape objective.",
                objects=[
                    _object("Spawn", "spawn", (0, 3, 0), (10, 1, 10), "Player start."),
                    _object("Dark Room", "room", (0, 2, 22), (28, 10, 24), "Explore area."),
                    _object(
                        "Jump Scare Trigger",
                        "trigger",
                        (0, 2, 34),
                        (8, 1, 4),
                        "Scare trigger.",
                    ),
                    _object("Chase Corridor", "chase", (0, 2, 58), (12, 8, 36), "Chase path."),
                    _object("Exit Door", "finish", (0, 3, 82), (10, 8, 2), "Escape objective."),
                ],
            )
        ],
    )


def _roleplay_layout() -> WorldLayout:
    return WorldLayout(
        title="Roleplay Layout",
        game_type="roleplay",
        zones=[
            MapZone(
                name="City Zone",
                purpose=(
                    "Provide a compact roleplay city with homes, jobs, vehicles, "
                    "and social space."
                ),
                objects=[
                    _object("City Spawn", "spawn", (0, 3, 0), (12, 1, 12), "Player city start."),
                    _object("Houses", "housing", (-28, 2, 18), (28, 10, 20), "Roleplay homes."),
                    _object("Job Board", "job", (0, 3, 18), (10, 6, 2), "Choose jobs."),
                    _object(
                        "Vehicle Spawns",
                        "vehicle",
                        (28, 2, 18),
                        (24, 1, 16),
                        "Spawn vehicles.",
                    ),
                    _object(
                        "Town Square",
                        "social",
                        (0, 2, 42),
                        (34, 1, 24),
                        "Social meeting area.",
                    ),
                ],
            )
        ],
    )


def _object(
    name: str,
    object_type: str,
    position: Vector3,
    size: Vector3,
    purpose: str,
) -> WorldObject:
    return WorldObject(
        name=name,
        type=object_type,
        position=position,
        size=size,
        purpose=purpose,
    )


def _level_count(user_idea: str) -> int | None:
    match = re.search(r"\b(\d{1,2})\b", user_idea)
    if match is None:
        return None
    return int(match.group(1))
