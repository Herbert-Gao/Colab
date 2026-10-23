"""Materialise the job records for every stage of the campaign.

Each record under ``state/jobs/`` is the single source of truth for one job:
the training data, the hyper-parameters, the seeds, the backtest schedule and
the milestone steps.  ``run_job.sh`` and ``jobctl.py`` only read it.

Stage numbering used by the queues:

======  ==================================================
stage   run book stage
======  ==================================================
1       阶段1  源训练超参预实验 (learning rate x chunk size)
2       阶段2  端到端试运行 (trial source model + trial adaptation)
4       阶段2b 目标适应超参预实验 (adaptation pilot)
3       阶段3  正式训练：3 个源模型 + 3 x 10 = 30 个适应作业
======  ==================================================
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

STATE_JOBS = C.STATE / "jobs"

# Runtime fields that a re-planned job keeps: the plan is regenerated whenever
# a hyper-parameter is frozen, and the work already done must survive it.
RUNTIME_FIELDS = (
    "status", "history", "milestones", "final_checkpoint", "processed_checkpoints",
    "no_improve_count", "best_success", "loss_windows", "incidents", "started",
    "finished", "pid", "current_step",
)


def base_job(job_id: str, **kwargs) -> dict:
    job = {
        "job_id": job_id,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": "pending",
        "peak_lr": C.BASE_LR,
        "action_horizon": C.BASE_ACTION_HORIZON,
        "batch_size": C.BATCH_SIZE,
        "max_steps": C.MAX_STEPS,
        "seed": 0,
        "history": [],
        "milestones": {},
        "milestone_steps": [],
        "save_interval": C.SAVE_INTERVAL,
        "no_improve_count": 0,
        "best_success": None,
        "processed_checkpoints": [],
        "incidents": [],
    }
    job.update(kwargs)
    return job


def build_plan() -> list[dict]:
    """Every job the run book asks for, in execution order."""
    jobs: list[dict] = []

    # Stage 1: 3 learning rates x 3 action horizons on move_pillbottle_pad.
    for lr_factor in C.LR_FACTORS:
        for horizon in C.ACTION_HORIZONS:
            lr = round(C.BASE_LR * lr_factor, 12)
            tag = f"lr{lr_factor:g}x_h{horizon}"
            jobs.append(base_job(
                f"stage1_{tag}",
                stage=1, kind="pilot", repeat=C.PILOT_TRAIN_SEED,
                task=C.PILOT_TASK, repo_id=C.pilot_repo_id(),
                exp_name=f"aloha_pilot_stage1_{tag}",
                checkpoint_base_dir=str(C.RUNS / "stage1"),
                init_params=str(C.BASE_PARAMS),
                peak_lr=lr, action_horizon=horizon, seed=C.PILOT_TRAIN_SEED,
                max_steps=C.PILOT_STEPS + 1,
                backtest_tasks=[C.PILOT_TASK],
                backtest_seeds=C.pilot_backtest_seeds(),
                milestone_steps=[C.PILOT_STEPS], save_interval=C.SAVE_INTERVAL,
                lr_factor=lr_factor,
            ))

    # Stage 2: end-to-end trial, repeat r=0.  The trial source model is the
    # starting point of the stage 2b adaptation pilot.
    jobs.append(base_job(
        "stage2_source_fam1_r0", stage=2, kind="trial_source", repeat=C.TRIAL_REPEAT,
        family="1", task=None, repo_id=C.family_repo_id("1"),
        exp_name="aloha_trial_fam1_r0",
        checkpoint_base_dir=str(C.RUNS / "stage2"),
        init_params=str(C.BASE_PARAMS), seed=C.TRIAL_REPEAT, max_steps=C.TRIAL_STEPS + 1,
        backtest_tasks=C.FAMILIES["1"],
        backtest_seeds=C.periodic_backtest_seeds(),
        milestone_steps=[C.TRIAL_STEPS], save_interval=C.SAVE_INTERVAL,
    ))
    jobs.append(base_job(
        "stage2_target_place_mouse_pad_r0", stage=2, kind="trial_adapt",
        repeat=C.TRIAL_REPEAT, family="1", t=C.ADAPT_PILOT_TARGET_T,
        task=C.TARGET_TASKS[C.ADAPT_PILOT_TARGET_T],
        repo_id=C.target_repo_id(C.ADAPT_PILOT_TARGET_T),
        exp_name="aloha_trial_adapt_place_mouse_pad_r0",
        checkpoint_base_dir=str(C.RUNS / "stage2"),
        init_params=None, init_from_job="stage2_source_fam1_r0",
        seed=C.TRIAL_REPEAT, max_steps=C.TRIAL_STEPS + 1,
        backtest_tasks=[C.TARGET_TASKS[C.ADAPT_PILOT_TARGET_T]],
        backtest_seeds=C.periodic_backtest_seeds(),
        milestone_steps=[C.TRIAL_STEPS], save_interval=C.SAVE_INTERVAL,
        demo_ids=C.target_demo_ids(C.ADAPT_PILOT_TARGET_T),
    ))

    # Stage 2b (queue stage 4): the adaptation pilot.  Same grid as stage 1, but
    # it starts from the stage-2 trial source model and it is scored with the
    # 910000+ backtest seeds.
    pilot_t = C.ADAPT_PILOT_TARGET_T
    for lr_factor in C.LR_FACTORS:
        for horizon in C.ACTION_HORIZONS:
            lr = round(C.BASE_LR * lr_factor, 12)
            tag = f"lr{lr_factor:g}x_h{horizon}"
            jobs.append(base_job(
                f"stage2b_{tag}", stage=4, kind="adapt_pilot", repeat=C.TRIAL_REPEAT,
                family="1", t=pilot_t, task=C.TARGET_TASKS[pilot_t],
                repo_id=C.target_repo_id(pilot_t),
                exp_name=f"aloha_stage2b_{tag}",
                checkpoint_base_dir=str(C.RUNS / "stage2b"),
                init_params=None, init_from_job="stage2_source_fam1_r0",
                peak_lr=lr, action_horizon=horizon, seed=C.PILOT_TRAIN_SEED,
                max_steps=C.ADAPT_PILOT_STEPS + 1,
                backtest_tasks=[C.TARGET_TASKS[pilot_t]],
                backtest_seeds=C.adapt_pilot_backtest_seeds(),
                milestone_steps=[C.ADAPT_PILOT_STEPS], save_interval=C.SAVE_INTERVAL,
                demo_ids=C.target_demo_ids(pilot_t),
                lr_factor=lr_factor,
            ))

    # Stage 3: the source models.  This round uses openpi's official
    # hyper-parameters and 15,000 steps; two of them are trained side by side,
    # four cards each (see C.COTRAIN_GROUPS).
    r = C.FORMAL_REPEAT
    for family in C.SOURCE_FAMILIES:
        tasks = C.FAMILIES[family]
        job_id = f"stage3_source_fam{family}_r{r}"
        jobs.append(base_job(
            job_id, stage=3, kind="source", repeat=r,
            family=family, task=None, repo_id=C.family_repo_id(family),
            exp_name=f"aloha_r{r}_source_fam{family}",
            checkpoint_base_dir=str(C.RUNS / "stage3"),
            init_params=str(C.BASE_PARAMS), seed=r,
            max_steps=C.SOURCE_MAX_STEPS + 1,
            backtest_tasks=tasks,
            backtest_seeds=C.periodic_backtest_seeds(),
            milestone_steps=list(C.SOURCE_MILESTONE_STEPS),
            save_interval=C.SAVE_INTERVAL_STAGE3,
            peak_lr=C.OFFICIAL_PEAK_LR, action_horizon=C.OFFICIAL_ACTION_HORIZON,
            final_backtest_step=C.SOURCE_MAX_STEPS,
            **C.COTRAIN_GROUPS.get(job_id, {}),
        ))
    # The operator gave the third family a longer budget: its 15,000-step run
    # left stack_blocks_three at 0/5, so the model continues from its delivered
    # weights for another 15,000 steps (30,000 steps in total).  The step
    # numbers of this job are relative to the continuation.
    long_family = C.SOURCE_LONG_FAMILY
    if long_family:
        tasks = C.FAMILIES[long_family]
        jobs.append(base_job(
            f"stage3_source_fam{long_family}_r{r}_long", stage=3, kind="source",
            repeat=r, family=long_family, task=None,
            repo_id=C.family_repo_id(long_family),
            exp_name=f"aloha_r{r}_source_fam{long_family}_long",
            checkpoint_base_dir=str(C.RUNS / "stage3"),
            init_params=C.source_long_init_params(long_family),
            seed=r, max_steps=C.SOURCE_LONG_STEPS + 1,
            backtest_tasks=tasks,
            backtest_seeds=C.periodic_backtest_seeds(),
            milestone_steps=[C.SOURCE_LONG_STEPS], save_interval=C.SAVE_INTERVAL_STAGE3,
            peak_lr=C.OFFICIAL_PEAK_LR, action_horizon=C.OFFICIAL_ACTION_HORIZON,
            final_backtest_step=C.SOURCE_LONG_STEPS,
            **C.SOURCE_LONG_GROUP,
        ))
    for t, task in enumerate(C.TARGET_TASKS):
        for family in C.ADAPT_SOURCE_FAMILIES:
            jobs.append(base_job(
                f"stage3_adapt_{task}_r{r}_from_fam{family}", stage=3, kind="adapt",
                repeat=r, family=family, t=t, task=task,
                repo_id=C.target_repo_id(t),
                exp_name=f"aloha_r{r}_adapt_{task}_from_fam{family}",
                checkpoint_base_dir=str(C.RUNS / "stage3"),
                init_params=None, init_from_job=f"stage3_source_fam{family}_r{r}",
                seed=r, max_steps=C.ADAPT_MAX_STEPS + 1,
                backtest_tasks=[task],
                backtest_seeds=C.periodic_backtest_seeds(),
                milestone_steps=list(C.ADAPT_MILESTONE_STEPS),
                save_interval=C.SAVE_INTERVAL_STAGE3,
                peak_lr=C.OFFICIAL_PEAK_LR, action_horizon=C.OFFICIAL_ACTION_HORIZON,
                final_backtest_step=C.ADAPT_MAX_STEPS,
                demo_ids=C.target_demo_ids(t),
            ))
    return jobs


def frozen_hparams() -> tuple[dict, dict]:
    source_path = C.STATE / "hparams.json"
    adapt_path = C.STATE / "hparams_adapt.json"
    source = json.loads(source_path.read_text()) if source_path.is_file() else {}
    adapt = json.loads(adapt_path.read_text()) if adapt_path.is_file() else {}
    return source, adapt


def apply_frozen(job: dict, source: dict, adapt: dict) -> None:
    """A frozen learning rate / action horizon replaces the job default.

    This round trains the source models with openpi's official
    hyper-parameters, so only the adaptation jobs take the frozen values (the
    stage 2b selection).  The grid jobs (stage 1 and the stage 2b pilot) keep
    their own values - they are what the selection is computed from.
    """
    if job.get("kind") != "adapt":
        return
    frozen = adapt
    if frozen.get("peak_lr"):
        job["peak_lr"] = frozen["peak_lr"]
    if frozen.get("action_horizon"):
        job["action_horizon"] = frozen["action_horizon"]


def main() -> int:
    for directory in C.ALL_DIRS + [STATE_JOBS]:
        directory.mkdir(parents=True, exist_ok=True)
    source, adapt = frozen_hparams()
    jobs = build_plan()
    for job in jobs:
        apply_frozen(job, source, adapt)
    for job in jobs:
        path = STATE_JOBS / f"{job['job_id']}.json"
        existing = json.loads(path.read_text()) if path.is_file() else {}
        if existing:
            job.update({k: v for k, v in existing.items() if k in RUNTIME_FIELDS})
            if existing.get("status") == "running":
                # A running trainer keeps the specification it was started
                # with; the record must not claim something else.
                for key in ("peak_lr", "action_horizon", "max_steps",
                            "milestone_steps", "save_interval", "train_gpus",
                            "fsdp_devices", "policy_gpus", "sim_gpus"):
                    if existing.get(key) is not None:
                        job[key] = existing[key]
        if job.get("kind") != "source" and job.get("status") == "pending":
            # This round trains the source models only: the pilots and the
            # adaptation jobs are deferred, not cancelled - their records stay
            # and can be resumed later.
            job["status"] = "deferred"
            job["defer_reason"] = "本轮只训练源模型（官方参数、15000 步、co-train），预实验与微调作业延后"
        C.json_dump(path, job)
    C.json_dump(C.STATE / "plan.json", {
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "jobs": len(jobs),
        "stage1": sum(1 for j in jobs if j["stage"] == 1),
        "stage2": sum(1 for j in jobs if j["stage"] == 2),
        "stage2b": sum(1 for j in jobs if j["stage"] == 4),
        "stage3": sum(1 for j in jobs if j["stage"] == 3),
        "frozen_source_hparams": source,
        "frozen_adapt_hparams": adapt,
    })
    print(f"planned {len(jobs)} jobs -> {STATE_JOBS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
