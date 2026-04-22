"""Invoke the cia-map-gen skill to produce reference maps."""
from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

CIA_MAP_GEN = Path.home() / ".claude/skills/cia-map-gen/cia_map_gen.py"


def generate_map(prompt: str, out_path: Path, title: str | None = None,
                 no_header: bool = True) -> Path | None:
    """Run cia-map-gen and return the PNG path, or None on failure."""
    if not CIA_MAP_GEN.exists():
        return None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "python3", str(CIA_MAP_GEN),
        "--prompt", prompt,
        "--out", str(out_path),
    ]
    if title:
        cmd += ["--title", title]
    if no_header:
        cmd += ["--no-header"]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if result.returncode != 0 or not out_path.exists():
        print(f"[map_integration] cia-map-gen failed for '{prompt}': "
              f"{result.stderr.strip()[:300]}")
        return None
    return out_path
