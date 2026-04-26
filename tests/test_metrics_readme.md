# Test Case: test_metrics

## Purpose
Verifies the core metric calculation engine: Weighted mode (sum of genRatio/100), Fully AI mode (count genRatio==100), and Mostly AI mode (count genRatio >= threshold). Covers the canonical example from the spec (77% / 50% / 80%) and edge cases: all-human, all-AI, zero lines.

## Status
Passing (16 tests)

## Covered
- US-001 AC-001-1: Weighted mode — 10 mixed lines → 77.0%
- US-001 AC-001-2: Fully AI mode — 10 mixed lines → 50.0%
- US-001 AC-001-3: Mostly AI mode with threshold 60 → 80.0%
- US-001 AC-001-4: All human-written → 0% for all modes
- US-001 AC-001-5: All AI-generated → 100% for all modes
- US-001 AC-001-6: Zero lines → 0.0% for all modes
- Mostly AI threshold edge cases (0, 100)
- AllMetrics dataclass combining three modes
- MetricResult dataclass with value, numerator, denominator, threshold

## Manual
```bash
python3 -m pytest tests/test_metrics.py -v
```
