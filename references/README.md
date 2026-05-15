# PDB Reference Corpus (development-only)

Declassified President's Daily Brief PDFs and per-page PNG renderings.
This directory was used **only during development** of the skills in
`../skills/` to match real PDB typography, layout, and map aesthetics
against ground truth.

> **The skills do not depend on this directory at runtime.** It is not
> copied to `~/.claude/skills/`, and removing it has no effect on a
> normal install. Keep it only if you intend to study the originals or
> extend the skills.

## Contents

| Path | What it holds |
|------|---------------|
| `*.pdf` | 30 declassified PDB documents from the CIA reading room |
| `screenshots/<DOC_ID>/page_NNN.png` | Per-page PNG rendering of each PDF |
| `map_sample/page_NNN.png` | Subset of pages whose layouts are reference maps |
| `index.json` | Machine-readable manifest of PDFs → screenshot directories |

## Provenance

All documents are public-domain releases from the CIA's electronic reading
room (CIA-RDP series). File names preserve the original document IDs.
