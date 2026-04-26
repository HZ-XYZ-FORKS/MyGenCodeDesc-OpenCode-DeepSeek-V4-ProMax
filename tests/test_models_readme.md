# Test Case: test_models

## Purpose
Verifies the domain model data structures for both genCodeDesc protocol versions (v26.03 and v26.04), including LineLocation, LineRange, Summary, Repository, Blame, DetailAddEntry, DetailDeleteEntry, and the full GenCodeDescV2603/V2604 records. Also validates genRatio bounds (0-100, AC-006-5) and SUMMARY invariants.

## Status
Passing (22 tests)

## Covered
- US-006 AC-006-5: genRatio value outside valid range (0-100)
- US-007 AC-007-1/2: Git SHA and SVN integer revisionId formats
- US-009 AC-009-7: v26.04 add/delete entry data structures
- LineLocation / LineRange creation and length calculation
- Summary invariant: totalCodeLines >= fullGenerated + partialGenerated
- Repository and RepositoryV2604 with revisionTimestamp
- Blame with optional fields (timestamp, author, originalLineRange)
- Full record construction for both v26.03 and v26.04
- ValidationError raised for genRatio outside 0-100

## Manual
```bash
python3 -m pytest tests/test_models.py -v
```
