"""Run one pi0.5 RoboTwin ALOHA training job (thin wrapper over openpi's train.py).

Every job is a fresh process so a crashed job can be resumed from its last
recovery checkpoint with identical configuration.  The driver owns job identity,
checkpoint retention and documentation; this module only trains.
"""

from __future__ import annotations

import argparse
import atexit
import importlib.util
import itertools
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
import pi05_config as P  # noqa: E402

TRAINER = C.OPENPI / "scripts" / "train.py"


def install_loss_trace(trainer_module, start_step: int, trace_path: Path) -> None:
    """Record every optimizer update's loss at full precision.

    openpi's own log line prints ``loss=%.4f`` every ``log_interval`` steps,
    which is far too coarse for the section 6 rule (a 1% relative change on a
    loss near 6e-4 is below the printed resolution).  Wrapping ``jax.jit`` lets
    us capture the per-update ``info`` pytrees without a per-step device sync;
    a background thread drains them once a minute.
    """
    import threading

    import jax

    pending: list[tuple[int, object]] = []
    counter = itertools.count(start_step)
    original_jit = jax.jit
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    stop = threading.Event()

    def recording_jit(fn, **kwargs):
        inner = original_jit(fn, **kwargs)

        def wrapped(*args, **inner_kwargs):
            result = inner(*args, **inner_kwargs)
            # Only the trainer's ptrain_step returns (state, info); other jit
            # calls in the process (init, restore helpers) must not be recorded.
            if (isinstance(result, tuple) and len(result) == 2
                    and isinstance(result[1], dict) and "loss" in result[1]):
                pending.append((next(counter), result[1]))
            return result

        return wrapped

    def drain() -> None:
        # A fresh run starts a fresh trace: the section 6 loss window must be
        # taken from the run that produced the checkpoint, not from an earlier
        # run that happened to write the same file.
        mode = "w" if start_step == 0 else "a"
        with open(trace_path, mode, buffering=1 << 16, encoding="utf-8") as handle:
            while True:
                time.sleep(5 if stop.is_set() else 5)
                batch, pending[:] = pending[:], []
                for step, info in batch:
                    try:
                        values = jax.device_get(info)
                        handle.write(f"{step},{float(values['loss'])},"
                                     f"{float(values['grad_norm'])},{float(values['param_norm'])}\n")
                    except Exception as error:  # noqa: BLE001 - tracing must never kill training
                        handle.write(f"# drain error at step {step}: {type(error).__name__}: {error}\n")
                handle.flush()
                if stop.is_set():
                    return

    jax.jit = recording_jit
    trainer_module.jax.jit = recording_jit
    thread = threading.Thread(target=drain, daemon=True)
    thread.start()

    def shutdown() -> None:
        stop.set()
        jax.jit = original_jit
        trainer_module.jax.jit = original_jit
        thread.join(timeout=180)

    trainer_module._campaign_loss_trace_shutdown = shutdown
    atexit.register(shutdown)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--repo-id", required=True)
    parser.add_argument("--exp-name", required=True)
    parser.add_argument("--checkpoint-base-dir", type=Path, required=True)
    parser.add_argument("--init-params", type=Path, default=None)
    parser.add_argument("--peak-lr", type=float, default=C.BASE_LR)
    parser.add_argument("--action-horizon", type=int, default=C.BASE_ACTION_HORIZON)
    parser.add_argument("--max-steps", type=int, default=C.MAX_STEPS)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=C.BATCH_SIZE)
    parser.add_argument("--fsdp-devices", type=int, default=C.FSDP_DEVICES)
    parser.add_argument("--num-workers", type=int, default=C.NUM_WORKERS,
                        help="LeRobot loader workers; keeps the 8 GPUs fed with frames.")
    parser.add_argument("--save-interval", type=int, default=C.SAVE_INTERVAL,
                        help="Optimizer updates between checkpoints; stage 3 uses 1500 so that "
                             "the 7500/15000/30000 milestones exist.")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--start-step", type=int, default=0,
                        help="Step the trainer resumes from; anchors the loss trace.")
    parser.add_argument("--trace-path", type=Path, default=None)
    args = parser.parse_args()

    checkpoint_dir = args.checkpoint_base_dir / C.CONFIG_NAME / args.exp_name
    config = P.build_train_config(
        name=C.CONFIG_NAME,
        exp_name=args.exp_name,
        repo_id=args.repo_id,
        checkpoint_base_dir=args.checkpoint_base_dir,
        init_params=args.init_params,
        peak_lr=args.peak_lr,
        action_horizon=args.action_horizon,
        max_steps=args.max_steps,
        seed=args.seed,
        batch_size=args.batch_size,
        fsdp_devices=args.fsdp_devices,
        num_workers=args.num_workers,
        save_interval=args.save_interval,
        resume=args.resume,
        overwrite=not args.resume,
    )

    state_path = C.STATE / "jobs_runtime" / f"{args.job_id}.json"
    snapshot = {
        "job_id": args.job_id,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "checkpoint_dir": str(checkpoint_dir),
        "repo_id": args.repo_id,
        "init_params": str(args.init_params or C.BASE_PARAMS),
        "peak_lr": args.peak_lr,
        "action_horizon": args.action_horizon,
        "max_steps": args.max_steps,
        "seed": args.seed,
        "batch_size": args.batch_size,
        "fsdp_devices": args.fsdp_devices,
        "num_workers": args.num_workers,
        "resume": args.resume,
        "warmup_steps": C.WARMUP_STEPS,
        "decay_steps": C.DECAY_STEPS,
        "decay_lr": C.DECAY_LR,
        "save_interval": args.save_interval,
        "keep_period": args.save_interval,
        "log_interval": C.LOG_INTERVAL,
        "ema_decay": C.EMA_DECAY,
        "norm_stats": str(C.ASSETS / "RoboTwin_lerobot_v30" / "norm_stats.json"),
        "embodiment": "aloha-agilex",
        "devices": os.environ.get("CUDA_VISIBLE_DEVICES", "<all>"),
    }
    C.json_dump(state_path, {**snapshot, "status": "running"})
    print("[job] " + json.dumps(snapshot, ensure_ascii=False), flush=True)

    spec = importlib.util.spec_from_file_location("openpi_train_entry", TRAINER)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load trainer from {TRAINER}")
    trainer = importlib.util.module_from_spec(spec)
    sys.modules["openpi_train_entry"] = trainer
    spec.loader.exec_module(trainer)

    install_loss_trace(trainer, args.start_step,
                       args.trace_path or C.LOGS / f"{args.job_id}_loss_trace.csv")

    try:
        trainer.main(config)
    except BaseException as error:  # noqa: BLE001 - record then re-raise
        C.json_dump(state_path, {
            **json.loads(state_path.read_text()),
            "status": "failed",
            "failed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "error": f"{type(error).__name__}: {error}",
        })
        raise
    C.json_dump(state_path, {
        **json.loads(state_path.read_text()),
        "status": "completed",
        "finished": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    })


if __name__ == "__main__":
    main()
