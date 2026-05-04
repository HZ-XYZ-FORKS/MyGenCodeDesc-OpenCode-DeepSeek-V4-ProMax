# User Testing Manual — `aggregateGenCodeDesc`

## What This Demo Does

Runs `aggregateGenCodeDesc` against a realistic project — 10 developers, 8 Python files, 21 commits (Git) + 18 revisions (SVN), 1 month of development with varying AI usage (5%–85%). Covers all 12 deployment cells.

## Prerequisites

- macOS / Linux with `git` on PATH
- Python 3.10+
- `svn` for SVN cells (optional — skipped if absent)
- `pip3 install orjson` for faster processing (optional)

## Quick Start

```bash
cd UserTesting/
chmod +x setup_demo.sh run_demo.sh
./setup_demo.sh       # builds git + svn repos, genCodeDesc files, patches
./run_demo.sh         # exercises all 12 cells, prints metrics
```

## What setup_demo.sh Creates

| Asset | Path | Notes |
|-------|------|-------|
| Git repo | `demo_work/repo/` | 21 commits, 8 .py files, merge/rename/cherry-pick/blame |
| genCodeDesc v26.04 | `demo_work/gcd-v26.04/` | Input for Algorithm C |
| genCodeDesc v26.03 | `demo_work/gcd-v26.03/` | Input for Algorithms A, B |
| Git patches | `demo_work/patches/` | Per-revision unified diffs for Algorithm B |
| SVN repo | `demo_work/svn_repo/` | 18 revisions, same project structure |
| SVN genCodeDesc | `demo_work/gcd-svn/` | v26.03 records for SVN cells |
| SVN patches | `demo_work/svn-patches/` | Per-revision svn diffs |

## Demo Output (what you should see)

### Algorithm C (cell 3 — hermetic CI, no VCS)

```text
[AlgC] LOAD rev=abc123 entries=23
[AlgC] PROCESS file=auth.py line=1 state=ADDED origin=abc123 genRatio=100
[AlgC] PROCESS file=config.py line=1 state=ADDED origin=abc123 genRatio=80
...
[AlgC] LOAD rev=def456 entries=37
...
[AlgC] SUMMARY aggregate totalLines=257 weighted=59.7% fullyAI=30.7% mostlyAI=63.4%
```

### Algorithm A (cell 1 — live git blame)

```text
[AlgA] LOAD blame file=main.py lines=30
[AlgA] LOAD blame file=auth.py lines=25
...
[AlgA] SUMMARY aggregate totalLines=32 weighted=43.0% fullyAI=21.6% mostlyAI=46.3%
```

### Algorithm B (cell 2 — diff replay)

```text
[AlgB] LOAD ...
[AlgB] SUMMARY aggregate totalLines=...
```

### Validation tests

```text
alg-version-mismatch → EXIT 2     (Algorithm A given v26.04 rejected)
duplicate-revision    → EXIT 2     (Duplicate revisionId detected)
empty-directory       → EXIT 2     (No genCodeDesc files found)
```

## Manual Verification

From the project root:

```bash
# Algorithm C (no VCS access)
PYTHONPATH="$(pwd)" python3 -m aggregateGenCodeDesc.cli \
  --repoUrl "file://$PWD/UserTesting/demo_work/repo" --repoBranch main \
  --startTime 2026-01-01T00:00:00Z --endTime 2026-02-01T00:00:00Z \
  --threshold 60 --algorithm C --scope A \
  --genCodeDescDir UserTesting/demo_work/gcd-v26.04/ \
  --outputDir /tmp/demo-out/ \
  --logLevel INFO

# Algorithm C (suppress per-line PROCESS for cleaner output)
PYTHONPATH="$(pwd)" python3 -m aggregateGenCodeDesc.cli \
  ...same... --quiet

# Algorithm A (live git blame)
PYTHONPATH="$(pwd)" python3 -m aggregateGenCodeDesc.cli \
  --repoUrl "file://$PWD/UserTesting/demo_work/repo" --repoBranch main \
  --startTime 2026-01-01T00:00:00Z --endTime 2026-02-01T00:00:00Z \
  --threshold 60 --algorithm A --scope A \
  --genCodeDescDir UserTesting/demo_work/gcd-v26.03/ \
  --repoPath UserTesting/demo_work/repo/ \
  --outputDir /tmp/demo-out/

# Version mismatch → exit 2
PYTHONPATH="$(pwd)" python3 -m aggregateGenCodeDesc.cli \
  --repoUrl "file://$PWD/UserTesting/demo_work/repo" --repoBranch main \
  --startTime 2026-01-01T00:00:00Z --endTime 2026-02-01T00:00:00Z \
  --algorithm A --scope A \
  --genCodeDescDir UserTesting/demo_work/gcd-v26.04/ \
  --outputDir /tmp/demo-err/
```

## 12-Cell Coverage

| # | Cell | run_demo.sh | Covers |
|---|------|:---:|--------|
| 1 | git · local · A | `cell-01-git-local-A` | Live blame, --repoPath |
| 2 | git · local · B | `cell-02-git-local-B` | Diff replay, --commitPatchDir |
| 3 | git · local · C | `cell-03-git-local-C` | VCS-free, v26.04 streaming |
| 4 | git · remote · A | `cell-04-git-remote-A` | Auto-clone, no --repoPath |
| 5 | git · remote · B | (same as #2) | Patches only, no live repo |
| 6 | git · remote · C | (same as #3) | Air-gapped, VCS-free |
| 7 | svn · local · A | `cell-07-svn-local-A` | svn blame, --repoPath |
| 8 | svn · local · B | `cell-08-svn-local-B` | SVN patches + replay |
| 9 | svn · local · C | (same as #3) | VCS-free |
| 10 | svn · remote · A | `cell-10-svn-remote-A` | svn blame via file:// |
| 11 | svn · remote · B | (same as #8) | SVN patches only |
| 12 | svn · remote · C | (same as #3) | VCS-free |

## Clean Up

```bash
rm -rf demo_work/
```
