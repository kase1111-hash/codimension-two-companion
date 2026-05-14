# Codimension Two Companion

*The computational companion to* Codimension Two: The Hodge Conjecture and What We Can Build Around It *(Kase Branham, 2026, CC0).*

This is a Python pipeline that implements the computations described in the parent book — one pipeline step per chapter. The aim is to make the parent book's atlas executable, extensible, and verifiable.

**Status: complete.** 39 of 39 planned pipeline steps implemented (chapters 4–44 plus Appendix C aggregator). Full end-to-end build runs in ~6 seconds at quick preset; the orchestration layer, dependency resolution, live TUI, and book-build (PDF + EPUB) are all working.

---

## Quick start

```bash
# Install everything (cross-platform)
python install.py

# Or if you prefer pip directly:
pip install -r requirements.txt
```

The `install.py` script installs Python dependencies, then checks for native
libraries (libcairo, pandoc, xelatex) and prints platform-specific commands
to install whichever are missing. It's safe to re-run.

```bash
# (Windows: if pip isn't on PATH, use `py -m pip install ...`)

# List registered steps
python -m pipeline.runner --list

# Show pipeline status (one-shot)
python -m pipeline.status

# Live TUI dashboard (refreshes every 0.5s; Ctrl-C exits)
python -m pipeline.tui

# Run a single step
python -m pipeline.runner --only ch_04_codim_grid

# Run a step with step-specific arguments
python -m pipeline.runner --only ch_21_hassett_discriminants -- --quick --workers 4

# Run the full pipeline (or just part 4)
python -m pipeline.runner --all
python -m pipeline.runner --part 4

# Dry-run: show what would execute without running
python -m pipeline.runner --all --dry-run

# Force re-run a complete step
python -m pipeline.runner --only ch_21_hassett_discriminants --force
```

## Building the book

```bash
# One command: regen chapters → compile Book.md → build PDF + EPUB
python book/_build/build_all.py

# Requires pandoc + xelatex on PATH:
#   Linux:   apt install pandoc texlive-xetex texlive-fonts-extra
#   macOS:   brew install pandoc; brew install --cask mactex
#   Windows: winget install JohnMacFarlane.Pandoc; install MiKTeX or TeX Live
```

## LMFDB connector

For arithmetic side scale-up (extending ch_14, ch_18, ch_26, ch_38), the pipeline ships an LMFDB REST API client with on-disk caching and rate limiting:

```bash
# Look up one elliptic curve by LMFDB label
python -m pipeline.data_tools.lmfdb_connector curve 11.a1

# Generic query: rank-2 curves with torsion-order 5
python -m pipeline.data_tools.lmfdb_connector query ec_curvedata -f rank=2 -f torsion=5 --limit 5

# Export elliptic curves in ch_14 short-Weierstrass JSON format
python -m pipeline.data_tools.lmfdb_connector export-ch14 --rank 1 --limit 200 \
    --out data/cache/lmfdb_rank1.json

# Show local cache stats
python -m pipeline.data_tools.lmfdb_connector cache-stats
```

LMFDB has ~3.8M elliptic curves over ℚ, 1.1M+ modular newforms, plus extensive abelian variety, modular form, and Galois representation data. The connector caches responses in `data/cache/lmfdb/` keyed by URL hash, so re-running the same query is free.

## External data integration (optional)

The default pipeline runs entirely on bundled sample data + analytic computation. For users who want to extend ch_32 (toric CY sweep) with real Kreuzer-Skarke data:

```bash
# List available datasets
python -m pipeline.data_tools.download --list

# Auto-download (small files only — pip install certifi first if on Windows)
python -m pipeline.data_tools.download --dataset tuwien-hodge-summary
python -m pipeline.data_tools.download --dataset tuwien-hodge-k3

# Inspect any downloaded file (auto-detects .spec vs PALP polytope-list format)
python -m pipeline.data_tools.inspect data/raw/v05.gz --stats
python -m pipeline.data_tools.inspect data/raw/v05.gz --limit 3

# Direct parser CLIs if you know the format
python -m pipeline.data_tools.tuwien_parser data/raw/tuwien-hodge-summary/alltoric.spec.gz --stats
python -m pipeline.data_tools.palp_parser data/raw/v*.gz --stats

# Mirror-symmetry verification (CY 3-fold: (h11,h12) ↔ (h12,h11) closure check)
python -m pipeline.data_tools.mirror_check data/raw/v*.gz
python -m pipeline.data_tools.mirror_check data/raw/v*.gz --csv unmatched.csv

# Render the iconic Kreuzer-Skarke "shield" plot (SVG + optional PNG)
python -m pipeline.data_tools.hodge_plot data/raw/v*.gz --out ks_shield.svg --png ks_shield.png

# After dropping files into data/raw/, re-run ch_32 — it auto-detects everything
python -m pipeline.runner --only ch_32_toric_cy_sweep --force -- --quick
```

The TU Wien `v*.gz` files (PALP polytope-list format, organized by vertex count) can be manually downloaded from http://quark.itp.tuwien.ac.at/~kreuzer/V/ if your network blocks SSL or you prefer browser downloads. Drop them anywhere under `data/raw/`; ch_32 will find and aggregate them.

**Scope note**: TU Wien 4D reflexive polytopes correspond to **CY 3-folds** (with h¹¹, h¹²). ch_32's primary work is on **CY 4-folds** (5D polytopes, Schöller-Skarke 2018). The TU Wien data integrates as a parallel-domain cross-reference, not a direct CY 4-fold input. The full Schöller-Skarke 5D-polytope dataset is downloadable manually from http://rgc.itp.tuwien.ac.at/fourfolds/ but is not yet wired into the pipeline (filed as v1.2 work).

## Windows portability

All file I/O explicitly uses `encoding='utf-8'`. The pipeline runs identically on Windows, macOS, and Linux. Spec files and chapter descriptions contain Unicode (Néron-Severi, Beauville-Bogomolov, etc.) which would otherwise hit `'charmap' codec` errors under the default Windows cp1252.

---

## Project structure

```
codimension-two-companion/
├── pipeline/
│   ├── kase_utils.py            # Vendored parallel-tests utility library
│   ├── registry.py              # Step discovery, artifact paths, progress tracking
│   ├── runner.py                # Orchestrator (dependency-aware)
│   ├── status.py                # Dashboard
│   ├── data_tools/              # Tools for downloading external databases
│   ├── steps/                   # One subdirectory per pipeline step
│   │   ├── ch_04_codim_grid/
│   │   │   ├── spec.yaml        # Step metadata (inputs, outputs, deps)
│   │   │   ├── compute.py       # Entry point
│   │   │   └── __main__.py      # Allows `python -m pipeline.steps.ch_04_codim_grid`
│   │   ├── ch_17_voevodsky_status/
│   │   ├── ch_21_hassett_discriminants/
│   │   └── ...                  # 35 more to come
│   ├── artifacts/               # All step outputs land here
│   └── tests/                   # Per-step unit tests
├── data/
│   ├── raw/                     # External databases (Kreuzer-Skarke, K3 atlases, etc.)
│   ├── processed/               # Cleaned / converted versions
│   └── README.md                # Data acquisition instructions
├── docs/
│   ├── CHAPTER_INVENTORY.md     # Mapping book chapters → pipeline steps
│   ├── ARCHITECTURE.md          # Design document
│   └── USAGE.md                 # CLI examples
├── book/
│   └── chapters/                # The companion book itself (eventual)
├── _build/                      # Book build pipeline (mirrors parent book)
└── README.md                    # This file
```

---

## The 38 pipeline steps

See `docs/CHAPTER_INVENTORY.md` for the complete catalog. Each step corresponds to one chapter of the parent book that has computational content. Categories:

| Symbol | Category | Count | Examples |
|---|---|---|---|
| **V** | Visualization | 2 | `ch_04_codim_grid`, `ch_07_three_gifts_table` |
| **S** | Small computation | 11 | `ch_17_voevodsky_status`, `ch_24_moduli_status` |
| **M** | Medium computation | 9 | `ch_14_tate_mirror`, `ch_19_k3_atlas` |
| **L** | Large computation | 9 | `ch_21_hassett_discriminants`, `ch_26_tate_point_counting`, `ch_32_toric_cy_sweep` |
| **A** | Aggregator | 6 | `ch_34_pattern_analysis`, `ch_40_web_graph` |

Theory-only chapters (Chs 1, 2, 3, 5, 8, 11, 45) have no pipeline step.

---

## How a pipeline step is structured

Every step lives under `pipeline/steps/<step_id>/` with three files:

**`spec.yaml`** — declares the step:
```yaml
step_id: ch_21_hassett_discriminants
chapter: 21
title: "Hassett Discriminants for Cubic 4-folds"
category: L
inputs:
  parameters:
    d_max:
      default: 100
      quick: 50
      long: 1000
dependencies:
  upstream: []
  downstream:
    - ch_27_cubic_4fold_periods
outputs:
  - path: hassett_table.csv
parallelizable: true
priority: high
```

**`compute.py`** — the entry point, following the `parallel-tests` template:
- Uses `kase_utils.parallel_map` for parallel execution
- Supports `--quick` / `--standard` / `--long` presets
- Writes artifacts to `pipeline/artifacts/<step_id>/`
- Calls `registry.write_progress()` to update its status
- Supports `--resume` via checkpoints
- Catches errors per-item; doesn't crash the pipeline on partial failures

**`__init__.py`** / **`__main__.py`** — allow standalone invocation:
```bash
python -m pipeline.steps.ch_21_hassett_discriminants --quick --workers 4
```

---

## Adding a new step

1. `mkdir pipeline/steps/ch_NN_new_step`
2. Write `spec.yaml` declaring metadata, inputs, outputs, dependencies
3. Write `compute.py` following the template (look at existing steps for examples)
4. Add `__init__.py` and `__main__.py` (boilerplate)
5. Run `python -m pipeline.runner --only ch_NN_new_step` to test
6. Run `python -m pipeline.status` to confirm it appears

The runner auto-discovers steps via `registry.discover_steps()` — no central registration needed.

---

## Progress tracking

Each step writes to `pipeline/artifacts/<step_id>/progress.json`:

```json
{
  "step_id": "ch_21_hassett_discriminants",
  "status": "in_progress",
  "items_done": 47,
  "items_total": 100,
  "percent_complete": 47.0,
  "elapsed_seconds": 194,
  "errors": 0
}
```

Status values: `pending` · `running` · `in_progress` · `complete` · `error` · `partial`.

The dashboard (`python -m pipeline.status`) reads all `progress.json` files and renders the full pipeline state with color coding and per-step item counts. With `--watch` it refreshes every 2 seconds.

---

## Dependencies

External Python packages:
- `numpy` — numerical computation (kase_utils dependency)
- `pyyaml` — spec.yaml parsing
- `tqdm` — progress bars
- `cairosvg` — SVG → PNG rendering (for figure-generating steps)
- (later) `pari` / `sage` / `sympy` — for algebraic computation in heavier steps

External databases (downloaded via `pipeline/data_tools/`):
- **Kreuzer-Skarke**: ~50 MB compressed; required for `ch_32_toric_cy_sweep`
- **K3 lattice atlas**: smaller; useful for `ch_19_k3_atlas`, `ch_25_hyperkahler_lattices`
- See `data/README.md` for acquisition instructions.

---

## License

CC0 1.0 Universal. Use, modify, redistribute freely.

Companion to *Codimension Two: The Hodge Conjecture and What We Can Build Around It* (Kase Branham, 2026, CC0).
