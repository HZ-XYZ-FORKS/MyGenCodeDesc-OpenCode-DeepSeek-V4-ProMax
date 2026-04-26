# Test Case: test_integration

## Purpose
End-to-end integration test of the `aggregateGenCodeDesc` CLI tool using Algorithm C with v26.04 protocol. Verifies the full pipeline: load genCodeDesc from directory, run AlgC accumulation, compute metrics, write output JSON and patch files. Also tests error handling (missing input dir), SVN revision IDs, --logLevel DEBUG, and default --outputDir.

## Status
Passing (5 tests)

## Covered
- US-001: Core metric — end-to-end AlgC pipeline produces correct Weighted/FullyAI/MostlyAI values
- US-007 AC-007-2: SVN revisionId (numeric) accepted
- US-006 AC-006-2: REPOSITORY validation across full pipeline
- EXIT_SUCCESS (0) for valid runs
- EXIT_VALIDATION_ERROR (2) for missing/nonexistent input directory
- --logLevel DEBUG runs without error
- Default --outputDir creates ./out/
- Output files: genCodeDescV26.03.json + commitStart2EndTime.patch
- Aggregate revisionId format: "aggregate:<startTime>..<endTime>"

## Manual
```bash
python3 -m pytest tests/test_integration.py -v
```
