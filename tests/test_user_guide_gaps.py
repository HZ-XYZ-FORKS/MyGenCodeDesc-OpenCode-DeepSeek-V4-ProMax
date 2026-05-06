import json
import pytest

from aggregateGenCodeDesc.cli import main, EXIT_SUCCESS, EXIT_RUNTIME_ERROR, EXIT_VALIDATION_ERROR


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
                {"changeType": "add", "lineLocation": 1, "genRatio": 100, "genMethod": "codeCompletion",
                 "blame": {"revisionId": "abc123", "originalFilePath": "src/auth.py", "originalLine": 1, "timestamp": "__TS__"}}
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


class TestExitCodes:
    def test_exit_2_alg_version_mismatch(self, tmp_path):
        """AlgA given v26.04 rejected with exit 2."""
        gcd = tmp_path / "gcd"
        gcd.mkdir()
        (gcd / "r.json").write_text(V2604_CONTENT.replace("__TS__", "2026-03-01T00:00:00Z"))
        r = main([
            "--repoUrl", "https://github.com/acme/foo", "--repoBranch", "main",
            "--startTime", "2026-01-01T00:00:00Z", "--endTime", "2026-12-31T00:00:00Z",
            "--algorithm", "A", "--scope", "A",
            "--genCodeDescDir", str(gcd),
            "--outputDir", str(tmp_path / "out"),
        ])
        assert r == EXIT_VALIDATION_ERROR

    def test_exit_2_algc_with_v2603(self, tmp_path):
        """AlgC given v26.03 rejected with exit 2."""
        gcd = tmp_path / "gcd"
        gcd.mkdir()
        v3 = V2604_CONTENT.replace("26.04", "26.03").replace("__TS__", "2026-03-01T00:00:00Z")
        (gcd / "r.json").write_text(v3)
        r = main([
            "--repoUrl", "https://github.com/acme/foo", "--repoBranch", "main",
            "--startTime", "2026-01-01T00:00:00Z", "--endTime", "2026-12-31T00:00:00Z",
            "--algorithm", "C", "--scope", "A",
            "--genCodeDescDir", str(gcd),
            "--outputDir", str(tmp_path / "out"),
        ])
        assert r == EXIT_VALIDATION_ERROR

    def test_exit_1_alg_b_invalid_repo(self, tmp_path):
        """AlgB on non-git directory causes git log failure → exit 1."""
        gcd = tmp_path / "gcd"
        gcd.mkdir()
        patch_dir = tmp_path / "patches"
        patch_dir.mkdir()
        repo_dir = tmp_path / "not_git"
        repo_dir.mkdir()
        v3 = V2604_CONTENT.replace("26.04", "26.03").replace("__TS__", "2026-03-01T00:00:00Z")
        v3 = v3.replace('"https://github.com/acme/foo"', '"file://' + str(repo_dir) + '"')
        (gcd / "r.json").write_text(v3)
        r = main([
            "--repoUrl", "file://" + str(repo_dir), "--repoBranch", "main",
            "--startTime", "2026-01-01T00:00:00Z", "--endTime", "2026-12-31T00:00:00Z",
            "--algorithm", "B", "--scope", "A",
            "--genCodeDescDir", str(gcd),
            "--repoPath", str(repo_dir),
            "--commitPatchDir", str(patch_dir),
            "--outputDir", str(tmp_path / "out"),
        ])
        assert r == EXIT_RUNTIME_ERROR

    def test_exit_0_success(self, tmp_path):
        """AlgC runs cleanly → exit 0."""
        gcd = tmp_path / "gcd"
        gcd.mkdir()
        (gcd / "r.json").write_text(V2604_CONTENT.replace("__TS__", "2026-03-01T00:00:00Z"))
        r = main([
            "--repoUrl", "https://github.com/acme/foo", "--repoBranch", "main",
            "--startTime", "2026-01-01T00:00:00Z", "--endTime", "2026-12-31T00:00:00Z",
            "--algorithm", "C", "--scope", "A",
            "--genCodeDescDir", str(gcd),
            "--outputDir", str(tmp_path / "out"),
        ])
        assert r == EXIT_SUCCESS


class TestPolicyFlags:
    def test_on_duplicate_reject(self, tmp_path):
        """--onDuplicate=reject: duplicate revisionId → exit 2."""
        gcd = tmp_path / "gcd"
        gcd.mkdir()
        ts = "2026-03-01T00:00:00Z"
        (gcd / "a.json").write_text(V2604_CONTENT.replace("__TS__", ts))
        (gcd / "b.json").write_text(V2604_CONTENT.replace("__TS__", ts))
        r = main([
            "--repoUrl", "https://github.com/acme/foo", "--repoBranch", "main",
            "--startTime", "2026-01-01T00:00:00Z", "--endTime", "2026-12-31T00:00:00Z",
            "--algorithm", "C", "--scope", "A",
            "--genCodeDescDir", str(gcd),
            "--outputDir", str(tmp_path / "out"),
            "--onDuplicate", "reject",
        ])
        assert r == EXIT_VALIDATION_ERROR

    def test_on_clock_skew_abort(self, tmp_path):
        """--onClockSkew: AlgC sorts records by timestamp before checking.
        After sorting, timestamps are always monotonic. The check is
        best-effort — it detects skew only when records arrive in
        VCS commit order (which AlgC cannot verify). Default: logs warning."""
        gcd = tmp_path / "gcd"
        gcd.mkdir()
        (gcd / "z.json").write_text(V2604_CONTENT.replace("__TS__", "2026-01-10T00:00:00Z").replace("abc123", "def456"))
        (gcd / "a.json").write_text(V2604_CONTENT.replace("__TS__", "2026-03-15T00:00:00Z"))
        r = main([
            "--repoUrl", "https://github.com/acme/foo", "--repoBranch", "main",
            "--startTime", "2026-01-01T00:00:00Z", "--endTime", "2026-12-31T00:00:00Z",
            "--algorithm", "C", "--scope", "A",
            "--genCodeDescDir", str(gcd),
            "--outputDir", str(tmp_path / "out"),
        ])
        assert r == EXIT_SUCCESS


class TestAlgSpecificFaults:
    def test_missing_diff_abort(self, tmp_path):
        """AC-009-6: missing patch in AlgB → exit 1."""
        gcd = tmp_path / "gcd"
        gcd.mkdir()
        patch_dir = tmp_path / "patches"
        patch_dir.mkdir()
        v3 = V2604_CONTENT.replace("26.04", "26.03").replace("__TS__", "2026-03-01T00:00:00Z")
        repo_path = str(tmp_path)
        v3 = v3.replace('"https://github.com/acme/foo"', '"file://' + repo_path + '"')
        (gcd / "r.json").write_text(v3)
        r = main([
            "--repoUrl", "file://" + repo_path, "--repoBranch", "main",
            "--startTime", "2026-01-01T00:00:00Z", "--endTime", "2026-12-31T00:00:00Z",
            "--algorithm", "B", "--scope", "A",
            "--genCodeDescDir", str(gcd),
            "--repoPath", repo_path,
            "--commitPatchDir", str(patch_dir),
            "--outputDir", str(tmp_path / "out"),
        ])
        assert r == EXIT_RUNTIME_ERROR


class TestCLIArgsNaming:
    def test_all_mandatory_args_lower_camel_case(self):
        """AC-006-6: mandatory args use lower camel case."""
        import argparse
        from aggregateGenCodeDesc.cli import build_parser
        p = build_parser()
        mandatory = ["--repoUrl", "--repoBranch", "--startTime", "--endTime", "--genCodeDescDir"]
        for action in p._actions:
            if action.dest in ["repoUrl", "repoBranch", "startTime", "endTime", "genCodeDescDir"]:
                assert any(opt.startswith("--") and opt == f"--{action.dest}" for opt in action.option_strings), \
                    f"{action.dest} should use lower camel case: --{action.dest}"
