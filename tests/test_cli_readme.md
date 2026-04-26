# Test Case: test_cli

## Purpose
Verifies the logging subsystem (--logLevel with DEBUG/INFO/WARNING/ERROR, structured format with timestamps, stderr output) and the output subsystem (genCodeDescV26.03.json aggregate result structure matching the protocol spec, commitStart2EndTime.patch, SUMMARY/DETAIL/AGGREGATE sections, diagnostics warnings, file I/O).

## Status
Passing (14 tests)

## Covered
- US-010 AC-010-1: Default log level INFO
- US-010 AC-010-2: DEBUG level with timestamps
- US-010 AC-010-3/4/5: WARNING and ERROR levels, log suppression
- Log output goes to stderr
- Invalid log level falls back to INFO
- AGGREGATE_OUTPUT_FILENAME = "genCodeDescV26.03.json"
- PATCH_OUTPUT_FILENAME = "commitStart2EndTime.patch"
- Aggregate JSON structure: protocolVersion, SUMMARY, REPOSITORY, AGGREGATE
- AGGREGATE.metrics with weighted/fullyAI/mostlyAI
- AGGREGATE.diagnostics with warnings
- Write output to directory

## Manual
```bash
python3 -m pytest tests/test_cli.py -v
```
