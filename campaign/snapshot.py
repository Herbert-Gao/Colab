"""Create and verify weights-only (params + assets) checkpoint snapshots.

Copying an Orbax tree is only safe once the write has fully settled: the
``_CHECKPOINT_METADATA`` file appears *before* the ocdbt array-metadata
database (``ocdbt.process_0``) is renamed into place, so a copy started at that
moment silently produces a tree that loads with missing parameters.  This
module therefore

1. waits until the source inventory stops changing and no staging directory is
   left over,
2. copies the tree,
3. compares the full relative-path/size inventory of source and copy, and
4. restores the copy with Orbax to prove the weights really load.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import time
from pathlib import Path


def inventory(root: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    if not root.is_dir():
        return out
    for path in root.rglob("*"):
        if path.is_file():
            out[str(path.relative_to(root))] = path.stat().st_size
    return out


def staging_left(root: Path) -> bool:
    return any(root.parent.glob(f"{root.name}.orbax-checkpoint-tmp-*"))


def wait_until_settled(root: Path, *, timeout_s: float = 900.0, poll_s: float = 15.0) -> dict[str, int]:
    """Block until the source tree stops changing (and no staging dir remains)."""
    deadline = time.time() + timeout_s
    previous = inventory(root)
    while time.time() < deadline:
        time.sleep(poll_s)
        current = inventory(root)
        if current == previous and not staging_left(root):
            return current
        previous = current
    raise TimeoutError(f"checkpoint {root} did not settle within {timeout_s}s")


def copy_weights(source: Path, dest: Path, *, verify_load: bool = True) -> dict:
    """Copy params/assets of ``source`` into ``dest`` and prove the copy loads."""
    source_params = source / "params"
    if not source_params.is_dir():
        raise FileNotFoundError(f"no params in {source}")
    wait_until_settled(source_params)

    tmp = dest.parent / f"{dest.name}.tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    for item in ("params", "assets", "metrics"):
        if (source / item).is_dir():
            shutil.copytree(source / item, tmp / item)
    for item in ("_CHECKPOINT_METADATA", "commit_success.txt"):
        if (source / item).is_file():
            shutil.copy2(source / item, tmp / item)

    source_inventory = inventory(source_params)
    copy_inventory = inventory(tmp / "params")
    missing = sorted(set(source_inventory) - set(copy_inventory))
    extra = sorted(set(copy_inventory) - set(source_inventory))
    size_diff = {key: (source_inventory[key], copy_inventory[key])
                 for key in set(source_inventory) & set(copy_inventory)
                 if source_inventory[key] != copy_inventory[key]}
    if missing or extra or size_diff:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError(
            f"copy verification failed for {source}: missing={missing[:5]} extra={extra[:5]} "
            f"size_mismatch={list(size_diff.items())[:5]}")

    leaves = _restore_count(tmp / "params") if verify_load else 0
    if verify_load and leaves <= 0:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError(f"copied params at {tmp} do not restore")

    shutil.rmtree(dest, ignore_errors=True)
    os.replace(tmp, dest)
    return {
        "path": str(dest),
        "bytes": sum(copy_inventory.values()),
        "files": len(copy_inventory),
        "restored_leaves": leaves,
        "verified": True,
        "source_files": len(source_inventory),
    }


def _restore_count(params_dir: Path) -> int:
    """Restore the copied params and count the leaves.

    The restore runs on the CPU: while the trainer of the job holds ~58 GiB per
    card, a GPU restore runs out of memory (it failed for the 7,500-step
    milestone of the second source model).  The copy itself is I/O bound, so
    the CPU restore does not add much time.
    """
    os.environ["JAX_PLATFORMS"] = "cpu"
    import jax

    from openpi.models import model as _model

    loaded = _model.restore_params(params_dir)
    return len(jax.tree_util.tree_leaves(loaded))


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 22), b""):
            value.update(block)
    return value.hexdigest()
