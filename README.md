# PDB reference corpus

Thirty declassified President's Daily Brief issues (1961-1976) from the
CIA electronic reading room (CIA-RDP series, public domain), with a
150 dpi PNG of every page. The PDB Skill plugin on `master` was measured
against these scans. They live on this branch so that adding the plugin
marketplace (a shallow clone of `master`) does not download them.

- `references/DOC_*.pdf` -- the documents, named by original document ID
- `references/screenshots/DOC_*/page_NNN.png` -- per-page renderings
- `references/map_sample/` -- the map plates used to style cia-map-gen
- `references/index.json` -- manifest of PDFs and their screenshots

To work with the corpus next to `master`:

    git fetch origin reference-corpus
    git worktree add ../PDB-SKILL-corpus reference-corpus
