"""Single source of truth for the server-A pi0.5 / RoboTwin ALOHA campaign.

Everything that section 4.2 of the run book pins down (task lists, seeds,
demo-id selection) lives here so every tool and the driver agree.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

WORK = Path(os.environ.get("PI05_30_ROOT", "/data/szgx/gaohang/pi05_30"))
XWORLD = Path(os.environ.get("XWORLD_ROOT", "/data/szgx/xworld-gzh"))

OPENPI = XWORLD / "third_party/external/openpi"
OPENPI_PYTHON = OPENPI / ".venv/bin/python"
ROBOTWIN = XWORLD / "third_party/external/robotwin"
ROBOTWIN_PYTHON = XWORLD / "envs/robotwin/bin/python"

RAW_ROOT = XWORLD / "datasets/robotwin2_demo_clean/demo_clean"
XWORLD_LEROBOT = XWORLD / "datasets/lerobot"
BASE_PARAMS = XWORLD / "cache/openpi/openpi-assets/checkpoints/pi05_base/params"

# --- workspace layout -------------------------------------------------------
DATASETS = WORK / "datasets" / "lerobot"
ASSETS = WORK / "assets"
RUNS = WORK / "runs"
EVAL = WORK / "eval"
LOGS = WORK / "logs"
STATE = WORK / "state"
DOCS = WORK / "docs"
JOBS_DOCS = DOCS / "jobs"
SNAPSHOTS = WORK / "snapshots"

ALL_DIRS = [
    DATASETS, ASSETS, RUNS, EVAL, LOGS, STATE, DOCS, JOBS_DOCS, SNAPSHOTS,
    ASSETS / "RoboTwin_lerobot_v30",
]

# --- tasks ------------------------------------------------------------------
FAMILIES: dict[str, list[str]] = {
    "1": ["move_pillbottle_pad", "move_stapler_pad", "place_a2b_left", "place_fan"],
    "2": ["place_object_basket", "place_cans_plasticbox", "place_bread_skillet", "put_object_cabinet"],
    "3": ["blocks_ranking_size", "stack_blocks_three", "stack_bowls_two", "stack_bowls_three"],
    "4": ["adjust_bottle", "pick_diverse_bottles", "lift_pot", "shake_bottle"],
    "5": ["click_alarmclock", "press_stapler", "stamp_seal", "turn_switch"],
}

# 4.2: the 20-task source union used only for the shared normalization stats.
STATS_TASKS: list[str] = [
    "move_pillbottle_pad", "move_stapler_pad", "place_a2b_left", "place_fan",
    "place_object_basket", "place_cans_plasticbox", "place_bread_skillet", "put_object_cabinet",
    "blocks_ranking_size", "stack_blocks_three", "stack_bowls_two", "stack_bowls_three",
    "adjust_bottle", "pick_diverse_bottles", "lift_pot", "shake_bottle",
    "click_alarmclock", "press_stapler", "stamp_seal", "turn_switch",
]

# Target tasks, index t = 0..9 (order is normative).
TARGET_TASKS: list[str] = [
    "place_mouse_pad", "rotate_qrcode", "place_can_basket", "hanging_mug",
    "stack_blocks_two", "blocks_ranking_rgb", "pick_dual_bottles", "scan_object",
    "click_bell", "beat_block_hammer",
]

# This round trains three source models (families 1-3) and adapts every target
# from each of them: 3 x 10 = 30 adaptation jobs.  Families 4 and 5 contribute
# their 50 demos to the shared normalization stats only - they are not trained.
SOURCE_FAMILIES = ["1", "2", "3"]
ADAPT_SOURCE_FAMILIES = SOURCE_FAMILIES

PILOT_TASK = "move_pillbottle_pad"
DEMOS_PER_TASK = 50
TARGET_DEMOS = 5
# Which family a target task belongs to (for the in-family / cross-family
# analysis of the generalization report).
TARGET_FAMILY = {t: str(t // 2 + 1) for t in range(len(TARGET_TASKS))}
FORMAL_REPEAT = 1             # this round trains exactly one formal repeat (r=1)
TRIAL_REPEAT = 0

# --- recipe (frozen base values; stage 1 varies lr and action_horizon only) ---
BASE_LR = 2.5e-5
LR_FACTORS = (0.5, 1.0, 2.0)
BASE_ACTION_HORIZON = 10          # PI05_ACTION_HORIZON default in the box recipe
# Nearest smaller / larger horizon the code and configs support:
#   smaller: the code takes any int action_horizon (openpi/models/pi0_config.py:26)
#   larger:  15, the horizon used by the pi05_droid config (training/config.py:673)
ACTION_HORIZONS = (5, 10, 15)
WARMUP_STEPS = 1000
DECAY_STEPS = 30000
DECAY_LR = 2.5e-6
BATCH_SIZE = 32
SAVE_INTERVAL = 2000          # stage 1 / stage 2 cadence
BACKTEST_INTERVAL = 2000      # periodic backtest cadence (section 5)
# Stage 3 must deliver the section 4.1 milestones 7500 / 15000 / 30000 while the
# periodic backtest runs every 2000 steps.  The save interval has to divide both
# (7500 and 2000): the common divisors are 500 and below, so stage 3 saves
# every 500 steps - 1000 would never produce the 7500 milestone.
SAVE_INTERVAL_STAGE3 = 500
LOG_INTERVAL = 25
# Measured: the loader workers sit below 15% CPU, so image decoding is not the
# limit (12 workers gave the same 1.5 it/s as 4).  Keep the known-good value.
NUM_WORKERS = int(os.environ.get("PI05_NUM_WORKERS", "4"))
EMA_DECAY = 0.99
FSDP_DEVICES = int(os.environ.get("PI05_FSDP_DEVICES", "8"))
TRAIN_GPUS = os.environ.get("PI05_TRAIN_GPUS", "0,1,2,3,4,5,6,7")
# The backtest runs while the trainer is stopped, so the evaluation owns all
# eight GPUs: four policy servers (GPU 0/2/4/6) and one simulator per
# remaining GPU (1/3/5/7).
SIM_GPU = os.environ.get("PI05_SIM_GPU", "1")
POLICY_GPUS = os.environ.get("PI05_POLICY_GPUS", "0,2,4,6").split(",")
CONFIG_NAME = "pi05_aloha_robotwin_30"

MAX_STEPS = 30000
MILESTONE_STEPS = (7500, 15000, 30000)
PILOT_STEPS = 2000
TRIAL_STEPS = 2000
# Stage 2b (the adaptation pilot) fixes one target - place_mouse_pad, t=0 - and
# searches the same learning rate x action_horizon grid as stage 1.
ADAPT_PILOT_TARGET_T = 0
ADAPT_PILOT_STEPS = 2000
BACKTEST_EPISODES = 5
FINAL_EPISODES = 100
EARLY_STOP_MIN_STEP = 12000      # baseline taken at 10000, judged from 12000 on
EARLY_STOP_BASELINE_STEP = 10000
EARLY_STOP_PATIENCE = 3
EARLY_STOP_LOSS_TOL = 0.01
# The operator relaxed section 6: the early stop now only needs the success
# condition.  With the loss of this recipe moving by more than 10% per
# 2,000-step interval the loss condition never held, so no job ever stopped
# early.
EARLY_STOP_REQUIRE_LOSS_CONDITION = False
LOSS_WINDOW = 500
ROLLING_KEEP = 2

# --- this round: official openpi hyper-parameters, 15,000 steps ------------
# openpi's own defaults (openpi/training/config.py: CosineDecaySchedule with
# warmup 1,000, peak_lr 2.5e-05, decay 30,000 -> 2.5e-06; batch 32; ema 0.99;
# the pi05_aloha_robotwin_h10 model config with action_horizon 10).
OFFICIAL_PEAK_LR = 2.5e-5
OFFICIAL_ACTION_HORIZON = 10
SOURCE_MAX_STEPS = 15000
SOURCE_MILESTONE_STEPS = (7500, 15000)

# The fine-tuning jobs run with an 8,000-step cap (operator decision).  The
# early-stop rule of section 6 needs the 10,000-step baseline, so with this
# cap it can never fire: every adaptation job trains its full 8,000 steps.
ADAPT_MAX_STEPS = 8000
ADAPT_MILESTONE_STEPS = (7500,)

# Two source models are trained side by side, four cards each: the trainer of
# one job never shares a card with the other one, and every job runs its own
# backtest on its own cards.
COTRAIN_GROUPS = {
    "stage3_source_fam2_r1": {
        "train_gpus": "0,1,2,3", "fsdp_devices": 4,
        "policy_gpus": "0,2", "sim_gpus": "1,3", "mem_fraction": 0.72,
    },
    "stage3_source_fam3_r1": {
        "train_gpus": "4,5,6,7", "fsdp_devices": 4,
        "policy_gpus": "4,6", "sim_gpus": "5,7", "mem_fraction": 0.72,
    },
}

# --- the third family gets a longer budget --------------------------------
# Its 15,000-step run left stack_blocks_three at 0/5 while the loss was still
# falling, so the model continues from its delivered weights for another
# 15,000 steps (30,000 steps in total).  The step numbers of that job are
# relative to the continuation.
SOURCE_LONG_FAMILY = "3"
SOURCE_LONG_STEPS = 15000
SOURCE_LONG_GROUP = {
    "train_gpus": "0,1,2,3,4,5,6,7", "fsdp_devices": 8,
    "policy_gpus": "0,2,4,6", "sim_gpus": "1,3,5,7", "mem_fraction": 0.75,
}


def source_long_init_params(family: str) -> str:
    """The delivered weights the longer run continues from."""
    record = STATE / "jobs" / f"stage3_source_fam{family}_r{FORMAL_REPEAT}.json"
    if record.is_file():
        job = json.loads(record.read_text())
        path = ((job.get("final_checkpoint") or {}).get("params_only") or {}).get("path")
        if path:
            return str(Path(path) / "params")
    raise FileNotFoundError(f"no delivered weights for source family {family}")


# --- seeds (4.2, verbatim) ---------------------------------------------------
PILOT_TRAIN_SEED = 0


# Section 4.2 fixes three disjoint backtest schedules: the pilot uses
# 900000+, the adaptation pilot 910000+, the periodic backtests 500100+ and the
# (unused this round) final evaluation 100000 + 1000*t + i.
PILOT_BACKTEST_SEED_BASE = 900000
ADAPT_PILOT_BACKTEST_SEED_BASE = 910000
PERIODIC_BACKTEST_SEED_BASE = 500100


def pilot_backtest_seeds() -> list[int]:
    return [PILOT_BACKTEST_SEED_BASE + i for i in range(BACKTEST_EPISODES)]


def adapt_pilot_backtest_seeds() -> list[int]:
    return [ADAPT_PILOT_BACKTEST_SEED_BASE + i for i in range(BACKTEST_EPISODES)]


def periodic_backtest_seeds() -> list[int]:
    return [PERIODIC_BACKTEST_SEED_BASE + i for i in range(BACKTEST_EPISODES)]


def final_eval_seeds(t: int, n: int = FINAL_EPISODES) -> list[int]:
    return [100000 + 1000 * t + i for i in range(n)]


def target_demo_ids(t: int) -> list[int]:
    """4.2: rng(1000 + t), 5 without replacement, ascending episode ids."""
    rng = np.random.default_rng(1000 + t)
    picked = rng.choice(DEMOS_PER_TASK, size=TARGET_DEMOS, replace=False)
    return sorted(int(x) for x in picked)


def source_episode_ids() -> list[int]:
    return list(range(DEMOS_PER_TASK))


# --- dataset naming ---------------------------------------------------------
def pilot_repo_id() -> str:
    return f"pi05_30_pilot_{PILOT_TASK}"


def family_repo_id(family: str) -> str:
    tasks = FAMILIES[family]
    return "pi05_30_aloha_fam%s_%s_src50" % (family, "_".join(tasks))


def target_repo_id(t: int) -> str:
    return f"pi05_30_aloha_target_{TARGET_TASKS[t]}_n5"


def json_dump(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)
