from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RobloxGameType = Literal["obby", "tycoon", "simulator", "racing", "horror", "roleplay"]


class RobloxGamePlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str = Field(min_length=1)
    game_type: RobloxGameType
    core_loop: str = Field(min_length=1)
    map_sections: list[str] = Field(min_length=1)
    mechanics: list[str] = Field(min_length=1)
    objects: list[str] = Field(min_length=1)
    scripts_needed: list[str] = Field(min_length=1)
    testing_steps: list[str] = Field(min_length=1)


class RobloxBuildPackage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    plan: RobloxGamePlan
    scripts: Sequence[BaseModel] = Field(min_length=1)
    studio_instructions: list[str] = Field(min_length=1)


@dataclass(frozen=True)
class RobloxGameTemplate:
    title: str
    core_loop: str
    map_sections: tuple[str, ...]
    mechanics: tuple[str, ...]
    objects: tuple[str, ...]
    scripts_needed: tuple[str, ...]
    testing_steps: tuple[str, ...]


GAME_TYPE_KEYWORDS: dict[RobloxGameType, tuple[str, ...]] = {
    "obby": ("obby", "обби", "parkour", "паркур", "лава", "levels", "уров"),
    "tycoon": ("tycoon", "тайкун", "строишь", "строить", "restaurant", "ресторан"),
    "simulator": ("simulator", "симулятор", "прокач", "сила", "strength", "pets"),
    "racing": ("racing", "гонки", "машин", "track", "lap"),
    "horror": ("horror", "хоррор", "страш", "школ", "chase"),
    "roleplay": ("roleplay", "rp", "город", "city", "jobs", "houses"),
}


GAME_TEMPLATES: dict[RobloxGameType, RobloxGameTemplate] = {
    "obby": RobloxGameTemplate(
        title="Roblox Lava Obby",
        core_loop=(
            "Players move through 10 levels, touch checkpoints, avoid lava, "
            "cross moving platforms, reach the finish, and collect a reward."
        ),
        map_sections=(
            "Start Area with spawn and tutorial sign",
            "Checkpoint Lane across 10 levels",
            "Lava Section with red damage parts",
            "Moving Platforms over the lava",
            "Finish Zone with winner trigger",
            "Reward Area with badge-style celebration",
        ),
        mechanics=(
            "Checkpoint respawn progression",
            "Lava damage on touch",
            "Moving platform timing challenge",
            "Finish reward trigger",
        ),
        objects=(
            "SpawnLocation",
            "10 numbered platforms",
            "Checkpoint parts",
            "Lava parts",
            "Moving platform parts",
            "Finish part",
            "Reward display",
        ),
        scripts_needed=(
            "Checkpoint Script",
            "Lava Damage Script",
            "Finish Reward Script",
        ),
        testing_steps=(
            "Press Play and confirm the player spawns in the Start Area.",
            "Touch a checkpoint, fall into lava, and confirm respawn uses the checkpoint.",
            "Touch lava and confirm damage is applied.",
            "Reach the finish and confirm the finish reward message appears.",
        ),
    ),
    "tycoon": RobloxGameTemplate(
        title="Roblox Restaurant Tycoon",
        core_loop="Players earn cash, press buttons, buy droppers, and upgrade their base.",
        map_sections=("Base", "Buttons", "Droppers", "Money System", "Upgrades"),
        mechanics=(
            "Cash button purchases",
            "Passive income loop",
            "Upgrade unlock progression",
        ),
        objects=("Base plate", "Purchase buttons", "Droppers", "Cash display", "Upgrade models"),
        scripts_needed=("Cash Button Script", "Income Loop Script"),
        testing_steps=(
            "Press Play and confirm cash starts at zero.",
            "Touch a purchase button and confirm cash changes.",
            "Wait for the income loop and confirm passive cash increases.",
        ),
    ),
    "simulator": RobloxGameTemplate(
        title="Roblox Strength Simulator",
        core_loop="Players train strength, earn currency, buy upgrades, and collect pets or items.",
        map_sections=("Training Zone", "Currency Counter", "Upgrades", "Pets/Items"),
        mechanics=("Click or touch training", "Strength currency gain", "Upgrade multiplier"),
        objects=("Training part", "Currency display", "Upgrade buttons", "Pet/item stands"),
        scripts_needed=("Strength Currency Script",),
        testing_steps=(
            "Press Play and touch the training part.",
            "Confirm strength and currency increase.",
            "Buy an upgrade and confirm the reward loop still works.",
        ),
    ),
    "racing": RobloxGameTemplate(
        title="Roblox Racing Track",
        core_loop="Players drive around a track, pass checkpoints, complete laps, and finish.",
        map_sections=("Track", "Checkpoints", "Lap System", "Finish Line"),
        mechanics=("Checkpoint order", "Lap counter", "Finish line detection"),
        objects=("Race track", "Checkpoint parts", "Lap display", "Finish line part", "Cars"),
        scripts_needed=("Checkpoint Lap Script",),
        testing_steps=(
            "Press Play and drive through checkpoints in order.",
            "Complete a full lap and confirm the lap count increases.",
            "Cross the finish line and confirm race progress updates.",
        ),
    ),
    "horror": RobloxGameTemplate(
        title="Roblox School Horror",
        core_loop="Players explore dark rooms, trigger scares, avoid a chase, and escape.",
        map_sections=("Spawn", "Dark Rooms", "Chase Area", "Escape Objective"),
        mechanics=("Trigger scare zones", "Chase moment", "Escape objective completion"),
        objects=("SpawnLocation", "Dark room parts", "Trigger part", "Scare sound", "Exit door"),
        scripts_needed=("Jump Scare Trigger Script",),
        testing_steps=(
            "Press Play and walk from spawn into the dark room.",
            "Touch the trigger and confirm the scare effect fires once.",
            "Reach the escape objective and confirm the path is playable.",
        ),
    ),
    "roleplay": RobloxGameTemplate(
        title="Roblox City Roleplay",
        core_loop="Players choose jobs, visit houses, use vehicles, and meet in social spaces.",
        map_sections=("City", "Houses", "Jobs", "Vehicles", "Social Spaces"),
        mechanics=("Job selection", "Team assignment", "Vehicle/social interaction"),
        objects=("City blocks", "House models", "Job boards", "Vehicle spawns", "Town square"),
        scripts_needed=("Team Job Assignment Script",),
        testing_steps=(
            "Press Play and choose a job from the job board.",
            "Confirm the player team/job label changes.",
            "Walk to houses, vehicles, and social spaces to confirm layout flow.",
        ),
    ),
}


def detect_roblox_game_type(user_idea: str) -> RobloxGameType:
    haystack = _normalize(user_idea)
    for game_type, keywords in GAME_TYPE_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return game_type
    return "obby"


def build_roblox_game_plan(user_idea: str) -> RobloxGamePlan:
    game_type = detect_roblox_game_type(user_idea)
    template = GAME_TEMPLATES[game_type]
    return RobloxGamePlan(
        title=_title_for(user_idea=user_idea, game_type=game_type, template=template),
        game_type=game_type,
        core_loop=template.core_loop,
        map_sections=list(template.map_sections),
        mechanics=list(template.mechanics),
        objects=list(template.objects),
        scripts_needed=list(template.scripts_needed),
        testing_steps=list(template.testing_steps),
    )


def build_roblox_package(user_idea: str) -> RobloxBuildPackage:
    from vuls.roblox.lua_generator import (  # noqa: PLC0415
        generate_roblox_lua_scripts,
        studio_instructions_for_plan,
    )

    plan = build_roblox_game_plan(user_idea)
    scripts = generate_roblox_lua_scripts(plan)
    return RobloxBuildPackage(
        plan=plan,
        scripts=scripts,
        studio_instructions=studio_instructions_for_plan(plan, scripts),
    )


def _title_for(
    *,
    user_idea: str,
    game_type: RobloxGameType,
    template: RobloxGameTemplate,
) -> str:
    if game_type == "obby" and _level_count(user_idea) == 10:
        return "Roblox 10-Level Lava Obby"
    return template.title


def _level_count(user_idea: str) -> int | None:
    match = re.search(r"\b(\d{1,2})\b", user_idea)
    if match is None:
        return None
    return int(match.group(1))


def _normalize(value: str) -> str:
    return value.casefold()
