# Test Case: test_alg_b

## Purpose
Verifies Algorithm B (offline diff replay) core logic: parsing unified diff patches into hunks and files, replaying diffs to track line origin revisions through FileLineTracker, handling add/delete/rename operations, and preserving line identity through chained diffs.

## Status
Passing (11 tests)

## Covered
- US-009 AC-009-4: Sequential multi-file diff replay
- US-009 AC-009-5: Line-position tracking through diffs
- Parse unified diff: simple add, multi-hunk, rename, empty diff
- FileLineTracker: add_line, delete_line_at, delete_line_range, rename_file
- Replay diff: add lines → origin tracked to revision
- Replay diff: delete lines → all removed from tracker
- Replay diff: rename → lines preserved under new path
- Replay diff: multi-diff chain → origin from each commit correctly tracked
- Line shifting on insertion (existing lines shift right) and deletion (shift left)

## Manual
```bash
python3 -m pytest tests/test_alg_b.py -v
```
