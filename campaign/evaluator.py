"""Run RoboTwin ALOHA closed-loop evaluation against a trained checkpoint.

Wraps the box's proven path (policy websocket server + RoboTwin's
``eval_policy_client_openpi_robotwin.py``) with the campaign's explicit
per-episode seed schedule from section 4.2.
"""

from __future__ import annotations

import contextlib
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

ROBOTWIN_PYTHON = str(C.ROBOTWIN_PYTHON)
EVAL_DRIVER = Path(__file__).resolve().parent / "robotwin_eval.py"
DEPLOY_YML = "policy/ACT/deploy_policy.yml"

EVAL_ENV_BASE = {
    "PYTHONPATH": f"{C.ROBOTWIN}:{C.XWORLD}/envs/robotwin/lib/python3.10/site-packages",
    "LD_LIBRARY_PATH": (
        f"{C.XWORLD}/envs/robotwin/lib/python3.10/site-packages/torch/lib:"
        "/usr/local/cuda-12.9/targets/x86_64-linux/lib"
    ),
    "PYTHONUNBUFFERED": "1",
    "PYTHONWARNINGS": "ignore::UserWarning",
}


def _free_port() -> int:
    with contextlib.closing(socket.socket()) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _port_open(port: int, timeout: float = 1.0) -> bool:
    try:
        with contextlib.closing(socket.create_connection(("127.0.0.1", port), timeout=timeout)):
            return True
    except OSError:
        return False


def _server_ready(port: int) -> bool:
    """A real websocket handshake, not just a TCP connect.

    The server binds its socket before ``serve_forever`` starts accepting, so a
    plain connect succeeds while a client would still be refused.
    """
    try:
        import asyncio

        import websockets

        async def probe() -> bool:
            try:
                async with websockets.connect(f"ws://127.0.0.1:{port}", open_timeout=5,
                                             close_timeout=2) as connection:
                    await connection.close()
                return True
            except Exception:
                return False

        return asyncio.run(probe())
    except Exception:
        return False


def _kill_group(process: subprocess.Popen) -> None:
    """Terminate the server and every child it spawned (JAX forks helpers)."""
    import signal

    try:
        group = os.getpgid(process.pid)
    except (ProcessLookupError, PermissionError):
        group = None
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            if group is not None:
                os.killpg(group, sig)
            else:
                process.send_signal(sig)
        except (ProcessLookupError, PermissionError):
            break
        try:
            process.wait(timeout=20)
            break
        except subprocess.TimeoutExpired:
            continue


@contextlib.contextmanager
def policy_server(checkpoint_dir: Path, *, repo_id: str, action_horizon: int, gpu: str,
                  log_path: Path, ready_timeout: float = 900.0):
    """Run the openpi websocket policy server for one checkpoint.

    A full weights-only checkpoint needs roughly 13 GiB of device memory, which
    may not be available while the trainer holds the same GPUs.  The server is
    therefore started with a smaller footprint and finally on CPU.
    """
    # A complete weights-only checkpoint needs ~13 GiB on device; a smaller
    # fraction cannot help (the cap would be below the requirement), so the
    # only real fallback is running the policy on CPU.
    attempts = [
        {"JAX_PLATFORMS": "cuda", "XLA_PYTHON_CLIENT_MEM_FRACTION":
            os.environ.get("PI05_EVAL_MEM_FRACTION", "0.25"), "CUDA_VISIBLE_DEVICES": str(gpu)},
        {"JAX_PLATFORMS": "cpu", "XLA_PYTHON_CLIENT_MEM_FRACTION": "",
         "CUDA_VISIBLE_DEVICES": ""},
    ]
    last_error: Exception | None = None
    for attempt, overrides in enumerate(attempts):
        try:
            with _policy_server_once(checkpoint_dir, repo_id=repo_id, action_horizon=action_horizon,
                                     log_path=log_path.with_suffix(f".attempt{attempt}"),
                                     ready_timeout=ready_timeout, overrides=overrides) as port:
                yield port
            return
        except (RuntimeError, TimeoutError) as error:
            last_error = error
            print(f"[policy_server] attempt {attempt} failed: {error}", flush=True)
    raise RuntimeError(f"policy server could not start for {checkpoint_dir}: {last_error}")


@contextlib.contextmanager
def _policy_server_once(checkpoint_dir: Path, *, repo_id: str, action_horizon: int,
                        log_path: Path, ready_timeout: float, overrides: dict):
    port = _free_port()
    env = {
        **os.environ,
        "HF_LEROBOT_HOME": str(C.DATASETS),
        "HF_HOME": str(C.XWORLD / "cache/huggingface"),
        "OPENPI_DATA_HOME": str(C.XWORLD / "cache/openpi"),
        "XLA_PYTHON_CLIENT_PREALLOCATE": "false",
        "PYTHONUNBUFFERED": "1",
        "TMPDIR": str(C.XWORLD / "cache/tmp"),
    }
    env.update({key: value for key, value in overrides.items() if value != ""})
    log_path.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        [str(C.OPENPI_PYTHON), "-u", str(Path(__file__).resolve().parent / "policy_server.py"),
         "--checkpoint-dir", str(checkpoint_dir),
         "--repo-id", repo_id,
         "--action-horizon", str(action_horizon),
         "--port", str(port)],
        env=env, stdout=open(log_path, "w"), stderr=subprocess.STDOUT, cwd=str(C.WORK),
        start_new_session=True,
    )
    deadline = time.time() + ready_timeout
    while time.time() < deadline:
        if process.poll() is not None:
            # The server's JAX children can survive the parent; kill the group.
            _kill_group(process)
            raise RuntimeError(f"policy server exited early (rc={process.returncode}); see {log_path}")
        if _port_open(port) and _server_ready(port):
            break
        time.sleep(3)
    else:
        _kill_group(process)
        raise TimeoutError(f"policy server not ready after {ready_timeout}s; see {log_path}")
    try:
        yield port
    finally:
        _kill_group(process)


def run_task_eval(task: str, seeds: list[int], *, out_dir: Path, sim_gpu: str, port: int,
                  timeout_s: int = 5400) -> dict:
    """Evaluate one RoboTwin task over an explicit seed schedule."""
    out_dir.mkdir(parents=True, exist_ok=True)
    episodes_json = out_dir / "episodes.json"
    log_path = out_dir / "eval.log"
    cmd = [
        ROBOTWIN_PYTHON, "-u", str(EVAL_DRIVER),
        "--config", DEPLOY_YML, "--overrides",
        "--task_name", task,
        "--task_config", "demo_clean",
        "--train_config_name", "0",
        "--seed", "0",
        "--policy_name", "ACT",
        "--port", str(port),
        "--robo_name", "robotwin",
        "--eval_video_log", "False",
        "--output_dir", str(out_dir),
        "--test_num", str(len(seeds)),
        "--seed_list", str(seeds),
        "--episodes_json", str(episodes_json),
    ]
    env = {**os.environ, **EVAL_ENV_BASE, "CUDA_VISIBLE_DEVICES": str(sim_gpu)}
    started = time.time()
    timed_out = False
    with open(log_path, "w") as log:
        log.write(" ".join(cmd) + "\n\n")
        log.flush()
        # Own process group: if the evaluation is killed, the simulator children
        # must not survive as orphans (they would keep the GPU busy).
        child = subprocess.Popen(cmd, cwd=str(C.ROBOTWIN), env=env, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        try:
            child.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            log.write("\n[TIMEOUT]\n")
        finally:
            if child.poll() is None:
                try:
                    os.killpg(os.getpgid(child.pid), 9)
                except (ProcessLookupError, PermissionError):
                    child.kill()

    result: dict = {
        "task": task,
        "seeds": seeds,
        "log": str(log_path),
        "timed_out": timed_out,
        "seconds": round(time.time() - started, 1),
    }
    if episodes_json.is_file():
        payload = json.loads(episodes_json.read_text())
        played = [e for e in payload["episodes"] if e.get("valid")]
        result.update({
            "episodes": len(played),
            "successes": int(payload["successes"]),
            "success_rate": round(payload["successes"] / len(played), 4) if played else 0.0,
            "per_episode": [
                {"episode": e["episode"], "seed": e["seed"], "success": e["success"],
                 "steps": e.get("steps"), "instruction": e.get("instruction")}
                for e in played
            ],
            "skipped": [e for e in payload["episodes"] if not e.get("valid")],
        })
    else:
        result.update({"episodes": 0, "successes": 0, "success_rate": 0.0,
                       "per_episode": [], "error": "no episodes.json"})
    return result
