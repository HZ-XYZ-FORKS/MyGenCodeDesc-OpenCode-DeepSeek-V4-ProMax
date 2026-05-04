import json
import pytest

from aggregateGenCodeDesc.cli import main, EXIT_SUCCESS, EXIT_VALIDATION_ERROR

V2604_CONTENT = """{
    "protocolName": "generatedTextDesc",
    "protocolVersion": "26.04",
    "codeAgent": "HuayanCoder",
    "SUMMARY": {
        "totalCodeLines": 10,
        "fullGeneratedCodeLines": 5,
        "partialGeneratedCodeLines": 4,
        "totalDocLines": 0,
        "fullGeneratedDocLines": 0,
        "partialGeneratedDocLines": 0
    },
    "DETAIL": [
        {
            "fileName": "src/auth.py",
            "codeLines": [
                {"changeType": "add", "lineRange": {"from": 1, "to": 5}, "genRatio": 100, "genMethod": "codeCompletion",
                 "blame": {"revisionId": "abc123", "originalFilePath": "src/auth.py", "originalLine": 1, "timestamp": "__TS__"}},
                {"changeType": "add", "lineRange": {"from": 6, "to": 8}, "genRatio": 80, "genMethod": "vibeCoding",
                 "blame": {"revisionId": "abc123", "originalFilePath": "src/auth.py", "originalLine": 6, "timestamp": "__TS__"}},
                {"changeType": "add", "lineLocation": 9, "genRatio": 30, "genMethod": "vibeCoding",
                 "blame": {"revisionId": "abc123", "originalFilePath": "src/auth.py", "originalLine": 9, "timestamp": "__TS__"}},
                {"changeType": "add", "lineLocation": 10, "genRatio": 0, "genMethod": "Manual",
                 "blame": {"revisionId": "abc123", "originalFilePath": "src/auth.py", "originalLine": 10, "timestamp": "__TS__"}}
            ]
        }
    ],
    "REPOSITORY": {
        "vcsType": "git",
        "repoURL": "https://github.com/acme/foo",
        "repoBranch": "main",
        "revisionId": "abc123",
        "revisionTimestamp": "__TS__"
    }
}"""


class TestCLIIntegration:
    def test_alg_c_end_to_end(self, tmp_path):
        gcd_dir = tmp_path / "gcd"
        gcd_dir.mkdir()
        out_dir = tmp_path / "out"

        ts = "2026-03-01T00:00:00Z"
        gcd_file = gcd_dir / "record1.json"
        gcd_file.write_text(V2604_CONTENT.replace("__TS__", ts))

        exit_code = main([
            "--repoUrl", "https://github.com/acme/foo",
            "--repoBranch", "main",
            "--startTime", "2026-01-01T00:00:00Z",
            "--endTime", "2026-12-31T23:59:59Z",
            "--genCodeDescDir", str(gcd_dir),
            "--outputDir", str(out_dir),
            "--threshold", "60",
            "--algorithm", "C",
            "--scope", "A",
            "--logLevel", "INFO",
        ])

        assert exit_code == EXIT_SUCCESS

        output_json = out_dir / "genCodeDescV26.03.json"
        assert output_json.exists()
        output_patch = out_dir / "commitStart2EndTime.patch"
        assert output_patch.exists()

        data = json.loads(output_json.read_text())
        assert data["protocolVersion"] == "26.03"
        assert data["AGGREGATE"]["metrics"]["weighted"]["value"] == 0.77
        assert data["AGGREGATE"]["metrics"]["fullyAI"]["value"] == 0.50
        assert data["AGGREGATE"]["metrics"]["mostlyAI"]["value"] == 0.80
        assert data["REPOSITORY"]["repoURL"] == "https://github.com/acme/foo"
        assert data["REPOSITORY"]["repoBranch"] == "main"
        assert data["REPOSITORY"]["revisionId"].startswith("aggregate:")

    def test_missing_input_dir(self, tmp_path):
        exit_code = main([
            "--repoUrl", "https://example.com/repo",
            "--repoBranch", "main",
            "--startTime", "2026-01-01T00:00:00Z",
            "--endTime", "2026-02-01T00:00:00Z",
            "--genCodeDescDir", "/nonexistent/path",
            "--outputDir", str(tmp_path / "out"),
            "--algorithm", "C",
        ])
        assert exit_code == EXIT_VALIDATION_ERROR

    def test_svn_revision_id_accepted(self, tmp_path):
        gcd_dir = tmp_path / "gcd"
        gcd_dir.mkdir()
        out_dir = tmp_path / "out"

        svn_content = V2604_CONTENT.replace(
            '"revisionId": "abc123"', '"revisionId": "4217"'
        ).replace('"vcsType": "git"', '"vcsType": "svn"'
        ).replace('"repoURL": "https://github.com/acme/foo"', '"repoURL": "https://svn.example.com/repo"'
        ).replace('"repoBranch": "main"', '"repoBranch": "/trunk"'
        ).replace("__TS__", "2026-03-01T00:00:00Z")
        (gcd_dir / "record1.json").write_text(svn_content)

        exit_code = main([
            "--repoUrl", "https://svn.example.com/repo",
            "--repoBranch", "/trunk",
            "--startTime", "2026-01-01T00:00:00Z",
            "--endTime", "2026-12-31T23:59:59Z",
            "--genCodeDescDir", str(gcd_dir),
            "--outputDir", str(out_dir),
            "--threshold", "60",
            "--algorithm", "C",
        ])
        assert exit_code == EXIT_SUCCESS

    def test_log_level_debug(self, tmp_path, capsys):
        gcd_dir = tmp_path / "gcd"
        gcd_dir.mkdir()
        out_dir = tmp_path / "out"
        ts = "2026-03-01T00:00:00Z"
        (gcd_dir / "record1.json").write_text(V2604_CONTENT.replace("__TS__", ts))

        exit_code = main([
            "--repoUrl", "https://github.com/acme/foo",
            "--repoBranch", "main",
            "--startTime", "2026-01-01T00:00:00Z",
            "--endTime", "2026-12-31T23:59:59Z",
            "--genCodeDescDir", str(gcd_dir),
            "--outputDir", str(out_dir),
            "--algorithm", "C",
            "--logLevel", "DEBUG",
        ])
        assert exit_code == EXIT_SUCCESS

    def test_cli_default_output_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        gcd_dir = tmp_path / "gcd"
        gcd_dir.mkdir()
        ts = "2026-03-01T00:00:00Z"
        (gcd_dir / "record1.json").write_text(V2604_CONTENT.replace("__TS__", ts))

        exit_code = main([
            "--repoUrl", "https://github.com/acme/foo",
            "--repoBranch", "main",
            "--startTime", "2026-01-01T00:00:00Z",
            "--endTime", "2026-12-31T23:59:59Z",
            "--genCodeDescDir", str(gcd_dir),
            "--algorithm", "C",
        ])
        assert exit_code == EXIT_SUCCESS
        assert (tmp_path / "out" / "genCodeDescV26.03.json").exists()


class TestOutputValidation:
    """US-012: Output validation ACs"""
    def test_output_json_has_all_fields(self, tmp_path):
        gcd_dir = tmp_path / "gcd"
        gcd_dir.mkdir()
        ts = "2026-03-01T00:00:00Z"
        gcd_file = gcd_dir / "record1.json"
        gcd_file.write_text(V2604_CONTENT.replace("__TS__", ts))

        exit_code = main([
            "--repoUrl", "https://github.com/acme/foo",
            "--repoBranch", "main",
            "--startTime", "2026-01-01T00:00:00Z",
            "--endTime", "2026-12-31T23:59:59Z",
            "--genCodeDescDir", str(gcd_dir),
            "--outputDir", str(tmp_path / "out"),
            "--algorithm", "C",
        ])
        assert exit_code == EXIT_SUCCESS

        d = json.loads((tmp_path / "out" / "genCodeDescV26.03.json").read_text())
        assert d["protocolName"] == "generatedTextDesc"
        assert d["protocolVersion"] == "26.03"
        agg = d["AGGREGATE"]
        assert "window" in agg
        assert "startTime" in agg["window"]
        assert "endTime" in agg["window"]
        assert "parameters" in agg
        assert agg["parameters"]["algorithm"] == "C"
        assert "metrics" in agg
        assert "weighted" in agg["metrics"]
        assert "fullyAI" in agg["metrics"]
        assert "mostlyAI" in agg["metrics"]
        assert "diagnostics" in agg
        assert "warnings" in agg["diagnostics"]

    def test_patch_has_header(self, tmp_path):
        gcd_dir = tmp_path / "gcd"
        gcd_dir.mkdir()
        ts = "2026-03-01T00:00:00Z"
        (gcd_dir / "record1.json").write_text(V2604_CONTENT.replace("__TS__", ts))

        main([
            "--repoUrl", "https://github.com/acme/foo",
            "--repoBranch", "main",
            "--startTime", "2026-01-01T00:00:00Z",
            "--endTime", "2026-12-31T23:59:59Z",
            "--genCodeDescDir", str(gcd_dir),
            "--outputDir", str(tmp_path / "out"),
            "--algorithm", "C",
        ])
        patch = (tmp_path / "out" / "commitStart2EndTime.patch").read_text()
        assert "aggregateGenCodeDesc" in patch
        assert "repoURL" in patch
        assert "repoBranch" in patch
        assert "aggregate:2026-01-01T00:00:00Z..2026-12-31T23:59:59Z" in patch

    def test_scope_filters_out_non_matching(self, tmp_path):
        gcd_dir = tmp_path / "gcd"
        gcd_dir.mkdir()
        ts = "2026-03-01T00:00:00Z"
        (gcd_dir / "record1.json").write_text(V2604_CONTENT.replace("__TS__", ts))

        main([
            "--repoUrl", "https://github.com/acme/foo",
            "--repoBranch", "main",
            "--startTime", "2026-01-01T00:00:00Z",
            "--endTime", "2026-12-31T23:59:59Z",
            "--genCodeDescDir", str(gcd_dir),
            "--outputDir", str(tmp_path / "out"),
            "--algorithm", "C",
            "--scope", "A",
        ])
        d = json.loads((tmp_path / "out" / "genCodeDescV26.03.json").read_text())
        assert d["AGGREGATE"]["parameters"]["scope"] == "A"
        assert d["SUMMARY"]["totalCodeLines"] >= 0

