"""Serve one trained checkpoint over the openpi websocket policy protocol."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
import pi05_config as P  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("policy_server")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    parser.add_argument("--repo-id", required=True)
    parser.add_argument("--action-horizon", type=int, default=C.BASE_ACTION_HORIZON)
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    os.environ.setdefault("HF_LEROBOT_HOME", str(C.DATASETS))
    from openpi.policies import policy_config as _policy_config
    from openpi.serving import websocket_policy_server

    config = P.build_train_config(
        name=C.CONFIG_NAME,
        exp_name=args.checkpoint_dir.name,
        repo_id=args.repo_id,
        checkpoint_base_dir=args.checkpoint_dir.parent,
        action_horizon=args.action_horizon,
        overwrite=False,
    )
    logger.info("loading %s", args.checkpoint_dir)
    policy = _policy_config.create_trained_policy(config, str(args.checkpoint_dir), default_prompt=None)
    server = websocket_policy_server.WebsocketPolicyServer(
        policy=policy, host=args.host, port=args.port, metadata=policy.metadata
    )
    logger.info("policy server on %s:%d", args.host, args.port)
    sys.stdout.flush()
    time.sleep(2)
    server.serve_forever()


if __name__ == "__main__":
    main()
