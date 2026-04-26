# Test Case: test_alg_c

## Purpose
Verifies Algorithm C (v26.04 embedded blame) core logic: accumulating the surviving-line set by processing add/delete entries in revisionTimestamp order, expanding lineRange/originalLineRange inclusively, handling delete-before-add within a record, detecting position collisions and duplicate add entries, detecting SUMMARY/DETAIL mismatches, and filtering by blame.timestamp for [startTime, endTime] window.

## Status
Passing (11 tests)

## Covered
- US-009 AC-009-7: Add/delete operations build correct surviving set
- US-009 AC-009-8: Duplicate add entry for same position detected and warned
- US-009 AC-009-9: SUMMARY lineCount mismatch vs actual DETAIL entries detected
- Basic add-only accumulation
- Add then delete → line removed from surviving set
- Add then delete+add → line replaced with new origin
- Delete before add in same record (deletes applied first)
- lineRange expansion: single add entry → multiple surviving lines
- originalLineRange delete expansion: bulk delete
- Timestamp sorting: records sorted by revisionTimestamp regardless of input order
- Records after endTime ignored

## Manual
```bash
python3 -m pytest tests/test_alg_c.py -v
```
