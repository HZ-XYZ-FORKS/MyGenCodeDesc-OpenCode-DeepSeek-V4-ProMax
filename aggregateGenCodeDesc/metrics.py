from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MetricResult:
    value: float
    numerator: float
    denominator: int = 0
    threshold: Optional[int] = None


def compute_weighted(gen_ratios: List[int]) -> MetricResult:
    if not gen_ratios:
        return MetricResult(value=0.0, numerator=0.0, denominator=0)
    n = len(gen_ratios)
    numerator = sum(r / 100.0 for r in gen_ratios)
    return MetricResult(value=round(numerator / n, 4), numerator=round(numerator, 4), denominator=n)


def compute_fully_ai(gen_ratios: List[int]) -> MetricResult:
    if not gen_ratios:
        return MetricResult(value=0.0, numerator=0, denominator=0)
    n = len(gen_ratios)
    numerator = sum(1 for r in gen_ratios if r == 100)
    return MetricResult(value=round(numerator / n, 4), numerator=numerator, denominator=n)


def compute_mostly_ai(gen_ratios: List[int], threshold: int) -> MetricResult:
    if not gen_ratios:
        return MetricResult(value=0.0, numerator=0, denominator=0, threshold=threshold)
    n = len(gen_ratios)
    numerator = sum(1 for r in gen_ratios if r >= threshold)
    return MetricResult(
        value=round(numerator / n, 4),
        numerator=numerator,
        denominator=n,
        threshold=threshold,
    )


@dataclass
class AllMetrics:
    weighted: MetricResult
    fully_ai: MetricResult
    mostly_ai: MetricResult


def compute_all_metrics(gen_ratios: List[int], threshold: int) -> AllMetrics:
    return AllMetrics(
        weighted=compute_weighted(gen_ratios),
        fully_ai=compute_fully_ai(gen_ratios),
        mostly_ai=compute_mostly_ai(gen_ratios, threshold),
    )
