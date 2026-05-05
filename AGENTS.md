# AGENTS.md — aggregateGenCodeDesc

## Commands

```bash
# Run all tests (187 tests, ~17s)
python3 -m pytest tests/ -v

# Run a single test file
python3 -m pytest tests/test_metrics.py -v

# Run only system tests (slower, need git on PATH)
python3 -m pytest tests/system/ -v

# Run the end-to-end demo
cd UserTesting && ./setup_demo.sh && ./run_demo.sh

# Install for development
pip install -e ".[fast,test]"

# CLI entry point (after pip install)
aggregateGenCodeDesc --help
aggregateGenCodeDesc --version
```

There is **no lint, typecheck, or build step** — only pytest.

## Architecture

```
aggregateGenCodeDesc/
├── cli.py              ← argparse entry point, main() orchestrates AlgA/B/C
├── models.py           ← v26.03/v26.04 dataclasses + validation
├── loader.py           ← JSON deserialization, protocol auto-detect, dir loading
├── metrics.py          ← Weighted / FullyAI / MostlyAI calculation
├── alg_a.py            ← Algorithm A: blame-line → genRatio resolution (no VCS calls)
├── alg_b.py            ← Algorithm B: unified diff parser + replay engine
├── alg_c.py            ← Algorithm C: v26.04 add/delete accumulation + streaming
├── blame_runner.py     ← git blame --porcelain + svn blame subprocess wrappers
├── vcs_ordering.py     ← git log --topo-order + svn log --xml commit ordering
├── policies.py         ← validation checks (clock skew, duplicates); enforcement in cli.py
├── output.py           ← genCodeDescV26.03.json + commitStart2EndTime.patch writer
└── logger.py           ← PhaseFilter (--quiet), ComponentFilter ([AlgA/B/C])
```

## Key Conventions

- **CaTDD workflow**: UserStories → AcceptanceCriteria → test RED → code GREEN → REFACTOR
- **No mocks**: Tests use real subprocess calls (git blame, svn blame, git log). System tests build real repos in `/tmp`.
- **genCodeDesc protocols**: v26.03 (sparse, AI lines only, no timestamps) for AlgA/B. v26.04 (incremental add/delete + embedded blame) for AlgC. Versions auto-detected from JSON.
- **SVN is first-class**: Not "legacy". Both git and svn have system tests, demo data, blame support.
- **69 ACs in README_UserStories.md**: This document IS the spec. Every test references specific ACs.

## Gotchas

- `alg_c.py` has TWO surviving-set builders: `accumulate_surviving_set()` (in-memory) and `stream_accumulate_surviving_set()` (streaming, used in production). Tests exercise both.
- `policies.py` functions only CHECK conditions; enforcement (exit 2, warning) happens in `cli.py main()`.
- `blame_runner.py` handles both git (`run_git_blame`) and svn (`run_svn_blame`) — separate parsers, same BlameLine output type.
- System tests (`tests/system/test_sys_vcs.py`) use a session-scoped fixture (`prod_repo`) built in `conftest.py`. SVN tests take ~8s each.
- Performance tests (`tests/system/test_perf.py`) generate 200K synthetic entries and verify streaming throughput. No I/O budget checks — just CPU bounds.
- `UserTesting/generate_demo.py` is the demo data generator — uses `git blame --porcelain` to produce blame-consistent genCodeDesc, not random data.
- `--logLevel` uses `INFO` (default), `DEBUG`, `WARNING`, `ERROR` — stderr only. `--quiet` suppresses per-line PROCESS, keeps LOAD + SUMMARY.
- Install `orjson` for 3-10x faster JSON parsing in AlgC streaming: `pip install orjson`. It's optional; `json` stdlib is the fallback.

## Where to Look First

- **Understand the spec**: `README_UserStories.md` (69 ACs)
- **Understand the CLI**: `aggregateGenCodeDesc/cli.py` main()
- **Understand AlgC (most used)**: `aggregateGenCodeDesc/alg_c.py` stream function
- **Understand testing**: `tests/system/conftest.py` fixture
- **User-facing demo**: `UserTesting/README.md`
