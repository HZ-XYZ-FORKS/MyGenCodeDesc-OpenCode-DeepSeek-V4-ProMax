import json
import logging
import pytest
from io import StringIO
from pathlib import Path

from aggregateGenCodeDesc.logger import (
    configure_logger,
    DEFAULT_LOG_FORMAT,
    get_logger,
)
from aggregateGenCodeDesc.models import (
    Summary,
    Repository,
    GenCodeDescV2603,
    DetailFileV2603,
    LineLocation,
)
from aggregateGenCodeDesc.output import (
    build_aggregate_output,
    AGGREGATE_OUTPUT_FILENAME,
    PATCH_OUTPUT_FILENAME,
)
from aggregateGenCodeDesc.metrics import AllMetrics, MetricResult


class TestLogger:
    def test_default_log_level_is_info(self):
        logger = configure_logger("INFO")
        assert logger.level == logging.INFO

    def test_debug_level(self):
        logger = configure_logger("DEBUG")
        assert logger.level == logging.DEBUG

    def test_warning_level(self):
        logger = configure_logger("WARNING")
        assert logger.level == logging.WARNING

    def test_error_level(self):
        logger = configure_logger("ERROR")
        assert logger.level == logging.ERROR

    def test_invalid_level_falls_back_to_info(self):
        logger = configure_logger("INVALID")
        assert logger.level == logging.INFO

    def test_log_output_to_stderr(self, capsys):
        logger = configure_logger("INFO")
        logger.info("test message")
        captured = capsys.readouterr()
        assert "test message" in captured.err

    def test_debug_includes_timestamp(self, capsys):
        logger = configure_logger("DEBUG")
        logger.debug("debug message")
        captured = capsys.readouterr()
        assert "debug message" in captured.err

    def test_error_suppresses_info(self, capsys):
        logger = configure_logger("ERROR")
        logger.info("should not appear")
        captured = capsys.readouterr()
        assert "should not appear" not in captured.err

    def test_get_logger_returns_configured_logger(self):
        configure_logger("INFO")
        logger = get_logger()
        assert logger.level == logging.INFO


class TestOutputFilename:
    def test_aggregate_output_filename(self):
        assert AGGREGATE_OUTPUT_FILENAME == "genCodeDescV26.03.json"

    def test_patch_output_filename(self):
        assert PATCH_OUTPUT_FILENAME == "commitStart2EndTime.patch"


class TestBuildAggregateOutput:
    def test_build_full_output(self, tmp_path):
        metrics = AllMetrics(
            weighted=MetricResult(value=0.77, numerator=7.7, denominator=10),
            fully_ai=MetricResult(value=0.50, numerator=5, denominator=10),
            mostly_ai=MetricResult(value=0.80, numerator=8, denominator=10, threshold=60),
        )
        output = build_aggregate_output(
            repo_url="https://github.com/acme/foo",
            repo_branch="main",
            start_time="2026-01-01T00:00:00Z",
            end_time="2026-04-01T00:00:00Z",
            algorithm="C",
            scope="A",
            threshold=60,
            input_protocol_version="26.04",
            metrics=metrics,
            warnings=[],
            gen_ratios=[100, 100, 100, 100, 100, 80, 80, 80, 30, 0],
            detail_files=[],
        )
        assert output["protocolVersion"] == "26.03"
        assert output["SUMMARY"]["totalCodeLines"] == 10
        assert output["SUMMARY"]["fullGeneratedCodeLines"] == 5
        assert output["SUMMARY"]["partialGeneratedCodeLines"] == 4
        assert output["AGGREGATE"]["metrics"]["weighted"]["value"] == 0.77
        assert output["AGGREGATE"]["metrics"]["fullyAI"]["value"] == 0.50
        assert output["AGGREGATE"]["metrics"]["mostlyAI"]["value"] == 0.80
        assert output["AGGREGATE"]["diagnostics"]["missingRevisions"] == []
        assert output["AGGREGATE"]["diagnostics"]["clockSkewDetected"] is False

    def test_output_with_diagnostics(self, tmp_path):
        metrics = AllMetrics(
            weighted=MetricResult(value=0.0, numerator=0.0, denominator=0),
            fully_ai=MetricResult(value=0.0, numerator=0, denominator=0),
            mostly_ai=MetricResult(value=0.0, numerator=0, denominator=0, threshold=60),
        )
        output = build_aggregate_output(
            repo_url="https://example.com/repo",
            repo_branch="main",
            start_time="2026-01-01T00:00:00Z",
            end_time="2026-01-02T00:00:00Z",
            algorithm="A",
            scope="A",
            threshold=60,
            input_protocol_version="26.03",
            metrics=metrics,
            warnings=["Missing genCodeDesc for revision abc123"],
            detail_files=[],
        )
        assert output["AGGREGATE"]["diagnostics"]["warnings"] == ["Missing genCodeDesc for revision abc123"]

    def test_write_output_to_dir(self, tmp_path):
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        metrics = AllMetrics(
            weighted=MetricResult(value=0.5, numerator=5.0, denominator=10),
            fully_ai=MetricResult(value=0.3, numerator=3, denominator=10),
            mostly_ai=MetricResult(value=0.6, numerator=6, denominator=10, threshold=60),
        )
        output = build_aggregate_output(
            repo_url="https://example.com/repo",
            repo_branch="main",
            start_time="2026-01-01T00:00:00Z",
            end_time="2026-02-01T00:00:00Z",
            algorithm="C",
            scope="A",
            threshold=60,
            input_protocol_version="26.04",
            metrics=metrics,
            warnings=[],
            detail_files=[],
        )
        json_path = output_dir / AGGREGATE_OUTPUT_FILENAME
        json_path.write_text(json.dumps(output, indent=2))

        patch_path = output_dir / PATCH_OUTPUT_FILENAME
        patch_path.write_text("diff --git a/file b/file\n")

        assert json_path.exists()
        assert patch_path.exists()
        loaded = json.loads(json_path.read_text())
        assert loaded["AGGREGATE"]["metrics"]["weighted"]["value"] == 0.5
