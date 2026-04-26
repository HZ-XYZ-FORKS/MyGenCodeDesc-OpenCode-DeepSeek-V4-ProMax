from aggregateGenCodeDesc.models import (
    LineLocation,
    LineRange,
    Summary,
)
from aggregateGenCodeDesc.metrics import (
    MetricResult,
    compute_weighted,
    compute_fully_ai,
    compute_mostly_ai,
    compute_all_metrics,
)


class TestWeightedMetric:
    def test_weighted_mixed_lines(self):
        gen_ratios = [100, 100, 100, 100, 100, 80, 80, 80, 30, 0]
        result = compute_weighted(gen_ratios)
        assert result.value == 0.77
        assert result.numerator == 7.7
        assert result.denominator == 10

    def test_weighted_all_human(self):
        gen_ratios = [0] * 50
        result = compute_weighted(gen_ratios)
        assert result.value == 0.0
        assert result.numerator == 0.0

    def test_weighted_all_ai(self):
        gen_ratios = [100] * 50
        result = compute_weighted(gen_ratios)
        assert result.value == 1.0
        assert result.numerator == 50.0

    def test_weighted_no_lines(self):
        gen_ratios = []
        result = compute_weighted(gen_ratios)
        assert result.value == 0.0
        assert result.numerator == 0.0
        assert result.denominator == 0


class TestFullyAI:
    def test_fully_ai_mixed(self):
        gen_ratios = [100, 100, 100, 100, 100, 80, 80, 80, 30, 0]
        result = compute_fully_ai(gen_ratios)
        assert result.value == 0.50
        assert result.numerator == 5

    def test_fully_ai_all_human(self):
        gen_ratios = [0] * 50
        result = compute_fully_ai(gen_ratios)
        assert result.value == 0.0
        assert result.numerator == 0

    def test_fully_ai_all_ai(self):
        gen_ratios = [100] * 50
        result = compute_fully_ai(gen_ratios)
        assert result.value == 1.0
        assert result.numerator == 50

    def test_fully_ai_no_lines(self):
        gen_ratios = []
        result = compute_fully_ai(gen_ratios)
        assert result.value == 0.0
        assert result.numerator == 0
        assert result.denominator == 0


class TestMostlyAI:
    def test_mostly_ai_threshold_60(self):
        gen_ratios = [100, 100, 100, 100, 100, 80, 80, 80, 30, 0]
        result = compute_mostly_ai(gen_ratios, threshold=60)
        assert result.value == 0.80
        assert result.numerator == 8
        assert result.threshold == 60

    def test_mostly_ai_threshold_100(self):
        gen_ratios = [100, 100, 100, 100, 100, 80, 80, 80, 30, 0]
        result = compute_mostly_ai(gen_ratios, threshold=100)
        assert result.value == 0.50
        assert result.numerator == 5

    def test_mostly_ai_threshold_0(self):
        gen_ratios = [100, 100, 100, 100, 100, 80, 80, 80, 30, 0]
        result = compute_mostly_ai(gen_ratios, threshold=0)
        assert result.value == 1.0
        assert result.numerator == 10

    def test_mostly_ai_no_lines(self):
        gen_ratios = []
        result = compute_mostly_ai(gen_ratios, threshold=60)
        assert result.value == 0.0
        assert result.numerator == 0
        assert result.denominator == 0


class TestComputeAllMetrics:
    def test_all_metrics_mixed(self):
        gen_ratios = [100, 100, 100, 100, 100, 80, 80, 80, 30, 0]
        result = compute_all_metrics(gen_ratios, threshold=60)
        assert result.weighted.value == 0.77
        assert result.fully_ai.value == 0.50
        assert result.mostly_ai.value == 0.80

    def test_all_metrics_all_human(self):
        gen_ratios = [0] * 50
        result = compute_all_metrics(gen_ratios, threshold=60)
        assert result.weighted.value == 0.0
        assert result.fully_ai.value == 0.0
        assert result.mostly_ai.value == 0.0

    def test_all_metrics_all_ai(self):
        gen_ratios = [100] * 50
        result = compute_all_metrics(gen_ratios, threshold=60)
        assert result.weighted.value == 1.0
        assert result.fully_ai.value == 1.0
        assert result.mostly_ai.value == 1.0

    def test_all_metrics_no_lines(self):
        gen_ratios = []
        result = compute_all_metrics(gen_ratios, threshold=60)
        assert result.weighted.value == 0.0
        assert result.fully_ai.value == 0.0
        assert result.mostly_ai.value == 0.0
