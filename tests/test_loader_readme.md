# Test Case: test_loader

## Purpose
Verifies JSON loading and parsing of genCodeDesc files (v26.03 and v26.04), protocol version auto-detection, REPOSITORY field validation against expected values (AC-006-2), directory-level loading with mixed-version rejection, and CREDENTIAL section tolerance.

## Status
Passing (16 tests)

## Covered
- US-006 AC-006-2: REPOSITORY mismatch detection (repoURL, repoBranch, revisionId)
- Load v26.03 JSON with LineLocation and LineRange entries
- Load v26.04 JSON with DetailAddEntry and DetailDeleteEntry
- Load v26.04 with lineRange add entries and originalLineRange delete entries
- Auto-detect protocol version from JSON
- Load directory: all v26.03, all v26.04
- Reject mixed protocol versions in directory
- REPOSITORY.repoURL / repoBranch / revisionId mismatch → ValidationError
- Gracefully handle missing CREDENTIAL section

## Manual
```bash
python3 -m pytest tests/test_loader.py -v
```
