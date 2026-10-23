"""Build the campaign's pi0.5 TrainConfig.

Mirrors the canonical RoboTwin recipe on this box
(``scripts/train_pi05_robotwin_source.py``): ALOHA RoboTwin transforms, delta
actions on the 12 arm joints, per-episode task instruction as the prompt, and
``adapt_to_pi=False`` (RoboTwin aloha-agilex keeps the standard ALOHA joint
convention).  Only the parameters the campaign varies are exposed here.
"""

from __future__ import annotations

import dataclasses
import os
import sys
from pathlib import Path

import config as C

sys.path.insert(0, str(C.OPENPI / "src"))

from openpi import transforms as _transforms  # noqa: E402
from openpi.models import pi0_config  # noqa: E402
from openpi.training import config as train_config  # noqa: E402
from openpi.training import optimizer as train_optimizer  # noqa: E402
from openpi.training import weight_loaders  # noqa: E402

os.environ.setdefault("HF_LEROBOT_HOME", str(C.DATASETS))


@dataclasses.dataclass(frozen=True)
class RoboTwinPi05DataConfig(train_config.LeRobotAlohaDataConfig):
    """ALOHA transforms with LeRobot's per-episode task forwarded as prompt."""

    def create(self, assets_dirs: Path, model_config):
        result = super().create(assets_dirs, model_config)
        repack = _transforms.Group(
            inputs=[
                _transforms.RepackTransform(
                    {
                        "images": {
                            "cam_high": "observation.images.top",
                            "cam_left_wrist": "observation.images.left_wrist",
                            "cam_right_wrist": "observation.images.right_wrist",
                        },
                        "state": "observation.state",
                        "actions": "action",
                        "prompt": "task",
                    }
                )
            ]
        )
        return dataclasses.replace(result, repack_transforms=repack)


def build_train_config(
    *,
    name: str,
    exp_name: str,
    repo_id: str,
    checkpoint_base_dir: Path,
    init_params: Path | None = None,
    peak_lr: float = C.BASE_LR,
    action_horizon: int = C.BASE_ACTION_HORIZON,
    max_steps: int = C.MAX_STEPS,
    seed: int = 0,
    batch_size: int = C.BATCH_SIZE,
    fsdp_devices: int = C.FSDP_DEVICES,
    num_workers: int = C.NUM_WORKERS,
    save_interval: int = C.SAVE_INTERVAL,
    resume: bool = False,
    overwrite: bool = True,
) -> train_config.TrainConfig:
    """One frozen recipe; stage 1 varies only ``peak_lr`` and ``action_horizon``."""
    return train_config.TrainConfig(
        name=name,
        exp_name=exp_name,
        model=pi0_config.Pi0Config(pi05=True, action_horizon=action_horizon),
        data=RoboTwinPi05DataConfig(
            repo_id=repo_id,
            assets=train_config.AssetsConfig(
                assets_dir=str(C.ASSETS),
                asset_id="RoboTwin_lerobot_v30",
            ),
            adapt_to_pi=False,
            base_config=train_config.DataConfig(prompt_from_task=True),
        ),
        weight_loader=weight_loaders.CheckpointWeightLoader(
            str(init_params or C.BASE_PARAMS)
        ),
        assets_base_dir=str(C.ASSETS),
        checkpoint_base_dir=str(checkpoint_base_dir),
        seed=seed,
        batch_size=batch_size,
        fsdp_devices=fsdp_devices,
        num_workers=num_workers,
        num_train_steps=max_steps,
        lr_schedule=train_optimizer.CosineDecaySchedule(
            warmup_steps=C.WARMUP_STEPS,
            peak_lr=peak_lr,
            decay_steps=C.DECAY_STEPS,
            decay_lr=C.DECAY_LR,
        ),
        optimizer=train_optimizer.AdamW(
            b1=0.9, b2=0.95, eps=1e-8, weight_decay=1e-10, clip_gradient_norm=1.0
        ),
        log_interval=C.LOG_INTERVAL,
        save_interval=save_interval,
        keep_period=save_interval,
        wandb_enabled=False,
        overwrite=overwrite,
        resume=resume,
        ema_decay=C.EMA_DECAY,
    )
