from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from vuls.roblox.game_intelligence import RobloxGamePlan


class RobloxLuaScript(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    place_in_studio: str = Field(min_length=1)
    code: str = Field(min_length=1)


def generate_roblox_lua_scripts(plan: RobloxGamePlan) -> list[RobloxLuaScript]:
    if plan.game_type == "tycoon":
        return [_cash_button_script(), _income_loop_script()]
    if plan.game_type == "simulator":
        return [_strength_currency_script()]
    if plan.game_type == "racing":
        return [_checkpoint_lap_script()]
    if plan.game_type == "horror":
        return [_jump_scare_trigger_script()]
    if plan.game_type == "roleplay":
        return [_team_job_assignment_script()]
    return [_checkpoint_script(), _lava_damage_script(), _finish_reward_script()]


def studio_instructions_for_plan(
    plan: RobloxGamePlan,
    scripts: list[RobloxLuaScript],
) -> list[str]:
    script_names = ", ".join(script.name for script in scripts)
    return [
        "Open Roblox Studio.",
        "Create Baseplate.",
        "Add required Parts/Models from the game plan: " + ", ".join(plan.objects) + ".",
        "Add Script or LocalScript objects in the locations listed for each script.",
        f"Paste generated Lua for: {script_names}.",
        "Press Play.",
        "Test checkpoints/damage/rewards or the equivalent mechanics listed in the plan.",
    ]


def _checkpoint_script() -> RobloxLuaScript:
    return RobloxLuaScript(
        name="Checkpoint Script",
        purpose="Save the player's latest checkpoint when they touch checkpoint parts.",
        place_in_studio="ServerScriptService as a Script named CheckpointService.",
        code="""-- Where to put it: ServerScriptService > Script named CheckpointService
-- Expected object: Workspace.Checkpoints folder with checkpoint Parts
-- How to test: Press Play, touch a checkpoint, reset, and confirm respawn moves there

local Players = game:GetService("Players")
local checkpointsFolder = workspace:WaitForChild("Checkpoints")
local latestCheckpointByPlayer = {}

local function moveToCheckpoint(character, checkpoint)
    local root = character:FindFirstChild("HumanoidRootPart")
    if root then
        root.CFrame = checkpoint.CFrame + Vector3.new(0, 4, 0)
    end
end

for _, checkpoint in checkpointsFolder:GetChildren() do
    if checkpoint:IsA("BasePart") then
        checkpoint.Touched:Connect(function(hit)
            local character = hit.Parent
            local player = Players:GetPlayerFromCharacter(character)
            if player then
                latestCheckpointByPlayer[player.UserId] = checkpoint
            end
        end)
    end
end

Players.PlayerAdded:Connect(function(player)
    player.CharacterAdded:Connect(function(character)
        task.wait(0.2)
        local checkpoint = latestCheckpointByPlayer[player.UserId]
        if checkpoint then
            moveToCheckpoint(character, checkpoint)
        end
    end)
end)
""",
    )


def _lava_damage_script() -> RobloxLuaScript:
    return RobloxLuaScript(
        name="Lava Damage Script",
        purpose="Damage players when they touch lava parts.",
        place_in_studio="Inside each lava Part as a Script, or in ServerScriptService.",
        code="""-- Where to put it: Inside each lava Part as a Script
-- Expected object: Parent Part should be a red lava damage part
-- How to test: Press Play, touch the lava part, and confirm health decreases

local lava = script.Parent
local damage = 25
local debounce = {}

lava.Touched:Connect(function(hit)
    local character = hit.Parent
    local humanoid = character and character:FindFirstChildOfClass("Humanoid")
    if not humanoid then
        return
    end

    if debounce[humanoid] then
        return
    end

    debounce[humanoid] = true
    humanoid:TakeDamage(damage)
    task.wait(1)
    debounce[humanoid] = nil
end)
""",
    )


def _finish_reward_script() -> RobloxLuaScript:
    return RobloxLuaScript(
        name="Finish Reward Script",
        purpose="Show a finish reward message when the player touches the finish part.",
        place_in_studio="Inside the Finish part as a Script.",
        code="""-- Where to put it: Workspace.Finish > Script
-- Expected object: Finish Part at the end of the obby
-- How to test: Press Play, touch Finish, and confirm a reward value is added

local finish = script.Parent
local rewarded = {}

finish.Touched:Connect(function(hit)
    local character = hit.Parent
    local player = game.Players:GetPlayerFromCharacter(character)
    if not player or rewarded[player.UserId] then
        return
    end

    rewarded[player.UserId] = true
    local leaderstats = player:FindFirstChild("leaderstats")
    if not leaderstats then
        leaderstats = Instance.new("Folder")
        leaderstats.Name = "leaderstats"
        leaderstats.Parent = player
    end

    local wins = leaderstats:FindFirstChild("Wins")
    if not wins then
        wins = Instance.new("IntValue")
        wins.Name = "Wins"
        wins.Parent = leaderstats
    end

    wins.Value += 1
end)
""",
    )


def _cash_button_script() -> RobloxLuaScript:
    return RobloxLuaScript(
        name="Cash Button Script",
        purpose="Let a player touch a button to spend cash on a tycoon upgrade.",
        place_in_studio="Inside each tycoon purchase button Part as a Script.",
        code="""-- Where to put it: Purchase Button Part > Script
-- Expected object: Button Part with an upgrade model nearby
-- How to test: Press Play, touch the button, and confirm the button hides

local button = script.Parent
local price = 50

button.Touched:Connect(function(hit)
    local player = game.Players:GetPlayerFromCharacter(hit.Parent)
    if not player then
        return
    end

    local cash = player:FindFirstChild("Cash")
    if cash and cash.Value >= price then
        cash.Value -= price
        button.Transparency = 1
        button.CanTouch = false
        button.CanCollide = false
    end
end)
""",
    )


def _income_loop_script() -> RobloxLuaScript:
    return RobloxLuaScript(
        name="Income Loop Script",
        purpose="Give each player passive tycoon income while testing the economy.",
        place_in_studio="ServerScriptService as a Script named IncomeLoop.",
        code="""-- Where to put it: ServerScriptService > Script named IncomeLoop
-- Expected object: Players will receive a Cash IntValue
-- How to test: Press Play and watch Cash increase every few seconds

game.Players.PlayerAdded:Connect(function(player)
    local cash = Instance.new("IntValue")
    cash.Name = "Cash"
    cash.Value = 0
    cash.Parent = player

    while player.Parent do
        task.wait(3)
        cash.Value += 10
    end
end)
""",
    )


def _strength_currency_script() -> RobloxLuaScript:
    return RobloxLuaScript(
        name="Strength Currency Script",
        purpose="Increase player strength and coins when they touch the training part.",
        place_in_studio="Inside the Training part as a Script.",
        code="""-- Where to put it: Workspace.TrainingPart > Script
-- Expected object: TrainingPart where players train strength
-- How to test: Press Play, touch TrainingPart, and confirm Strength and Coins increase

local trainingPart = script.Parent

game.Players.PlayerAdded:Connect(function(player)
    local strength = Instance.new("IntValue")
    strength.Name = "Strength"
    strength.Value = 0
    strength.Parent = player

    local coins = Instance.new("IntValue")
    coins.Name = "Coins"
    coins.Value = 0
    coins.Parent = player
end)

trainingPart.Touched:Connect(function(hit)
    local player = game.Players:GetPlayerFromCharacter(hit.Parent)
    if not player then
        return
    end

    player.Strength.Value += 1
    player.Coins.Value += 2
end)
""",
    )


def _checkpoint_lap_script() -> RobloxLuaScript:
    return RobloxLuaScript(
        name="Checkpoint Lap Script",
        purpose="Track racing checkpoints and count a lap when the finish line is touched.",
        place_in_studio="ServerScriptService as a Script named LapTracker.",
        code="""-- Where to put it: ServerScriptService > Script named LapTracker
-- Expected object: Workspace.RaceCheckpoints folder and Workspace.FinishLine part
-- How to test: Press Play, drive through checkpoints, and confirm laps increase

local checkpoints = workspace:WaitForChild("RaceCheckpoints")
local finishLine = workspace:WaitForChild("FinishLine")
local progress = {}

for _, checkpoint in checkpoints:GetChildren() do
    if checkpoint:IsA("BasePart") then
        checkpoint.Touched:Connect(function(hit)
            local player = game.Players:GetPlayerFromCharacter(hit.Parent)
            if player then
                progress[player.UserId] = checkpoint.Name
            end
        end)
    end
end

finishLine.Touched:Connect(function(hit)
    local player = game.Players:GetPlayerFromCharacter(hit.Parent)
    if not player then
        return
    end

    local laps = player:FindFirstChild("Laps") or Instance.new("IntValue")
    laps.Name = "Laps"
    laps.Parent = player
    laps.Value += 1
end)
""",
    )


def _jump_scare_trigger_script() -> RobloxLuaScript:
    return RobloxLuaScript(
        name="Jump Scare Trigger Script",
        purpose="Trigger a simple scare effect when the player touches a hidden part.",
        place_in_studio="Inside a hidden trigger Part as a Script.",
        code="""-- Where to put it: Hidden scare trigger Part > Script
-- Expected object: Trigger Part in a dark room
-- How to test: Press Play, touch the trigger, and confirm the part flashes once

local trigger = script.Parent
local used = {}

trigger.Touched:Connect(function(hit)
    local player = game.Players:GetPlayerFromCharacter(hit.Parent)
    if not player or used[player.UserId] then
        return
    end

    used[player.UserId] = true
    trigger.BrickColor = BrickColor.new("Really red")
    task.wait(0.4)
    trigger.BrickColor = BrickColor.new("Black")
end)
""",
    )


def _team_job_assignment_script() -> RobloxLuaScript:
    return RobloxLuaScript(
        name="Team Job Assignment Script",
        purpose="Assign a roleplay job label when the player touches a job board.",
        place_in_studio="Inside each job board Part as a Script.",
        code="""-- Where to put it: Job Board Part > Script
-- Expected object: Job Board Part named after the job, such as Police or Chef
-- How to test: Press Play, touch the job board, and confirm Job value changes

local jobBoard = script.Parent
local jobName = jobBoard.Name

jobBoard.Touched:Connect(function(hit)
    local player = game.Players:GetPlayerFromCharacter(hit.Parent)
    if not player then
        return
    end

    local job = player:FindFirstChild("Job")
    if not job then
        job = Instance.new("StringValue")
        job.Name = "Job"
        job.Parent = player
    end

    job.Value = jobName
end)
""",
    )
