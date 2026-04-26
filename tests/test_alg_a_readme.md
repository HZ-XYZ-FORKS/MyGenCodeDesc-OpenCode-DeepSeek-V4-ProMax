# Test Case: test_alg_a

## Purpose
Verifies Algorithm A (live VCS blame) core logic: building a line-to-genRatio lookup map from v26.03 records, filtering blame lines by time window [startTime, endTime], resolving genRatio from sparse v26.03 DETAIL entries (unmatched lines default to genRatio=0), and computing aggregate metrics.

## Status
Passing (7 tests)

## Covered
- US-009 AC-009-1: Blame line tracking and genRatio resolution
- Build genratio map from v26.03 records with LineLocation and LineRange expansion
- Multi-file genratio map spanning multiple revisions
- Mark window lines: filter by blame origin timestamp in [startTime, endTime]
- Resolve genRatios: existing entries → genRatio, missing entries → genRatio=0
- Compute AlgA metrics from blame lines + genratio map
- BlameLine dataclass with gen_ratio default 0

## Manual
```bash
python3 -m pytest tests/test_alg_a.py -v
```
