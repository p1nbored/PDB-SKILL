"""Invoke the sibling cia-map-gen skill to render reference maps."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MAP_TIMEOUT_S = 180

# Both skills ship in the same plugin (<plugin>/skills/<name>/scripts/); a manual
# install under ~/.claude/skills keeps the same relative layout.
_CANDIDATES = (
    Path(__file__).resolve().parents[2] / "cia-map-gen" / "scripts" / "cia_map_gen.py",
    Path.home() / ".claude" / "skills" / "cia-map-gen" / "scripts" / "cia_map_gen.py",
)


def find_cia_map_gen() -> Path | None:
    return next((cand for cand in _CANDIDATES if cand.exists()), None)


def generate_map(prompt: str, out_path: Path, title: str | None = None,
                 no_header: bool = True) -> Path | None:
    """Run cia-map-gen and return the PNG path, or None on failure."""
    script = find_cia_map_gen()
    if script is None:
        print("[map] cia-map-gen not found next to pdb-replica-gen", file=sys.stderr)
        return None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(script), "--prompt", prompt, "--out", str(out_path)]
    if title:
        cmd += ["--title", title]
    if no_header:
        cmd.append("--no-header")
    try:
        # Decode explicitly: the locale codec (cp936/cp1252) would raise on
        # non-ASCII stderr and abort the whole brief.
        result = subprocess.run(cmd, capture_output=True, encoding="utf-8",
                                errors="replace", timeout=MAP_TIMEOUT_S,
                                check=False)
    except (subprocess.TimeoutExpired, OSError, ValueError) as exc:
        print(f"[map] cia-map-gen did not finish for {prompt!r}: {exc}", file=sys.stderr)
        return None
    if result.returncode != 0 or not out_path.exists():
        print(f"[map] cia-map-gen failed for {prompt!r}: "
              f"{(result.stderr or '').strip()[:300]}", file=sys.stderr)
        return None
    return out_path
