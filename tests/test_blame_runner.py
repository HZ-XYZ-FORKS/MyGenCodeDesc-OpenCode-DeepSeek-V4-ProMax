import subprocess
import pytest
from unittest.mock import patch, MagicMock

from aggregateGenCodeDesc.alg_a import BlameLine
from aggregateGenCodeDesc.blame_runner import (
    parse_blame_porcelain,
    run_git_blame,
    run_git_blame_on_files,
    iso_from_unix,
    GitBlameError,
)

PORCELAIN_OUTPUT = """abc1234567890abcdef1234567890abcdef1234 1 1 1
author John Smith
author-mail <john@example.com>
author-time 1735689600
author-tz +0000
filename app.py
\tdef foo():
def4567890abcdef1234567890abcdef1234567 2 2 2
author Jane Doe
author-mail <jane@example.com>
author-time 1735776000
author-tz +0000
filename app.py
\t    return 42
"""

RENAME_OUTPUT = """abc1234567890abcdef1234567890abcdef1234 5 5 1
author John Smith
author-mail <john@example.com>
author-time 1735689600
author-tz +0000
previous def4567890abcdef1234567890abcdef1234567 old_app.py
filename app.py
\tx = compute()
"""


class TestParseBlamePorcelain:
    def test_parse_two_lines(self):
        lines = parse_blame_porcelain(PORCELAIN_OUTPUT)
        assert len(lines) == 2
        assert lines[0].origin_revision == "abc1234567890abcdef1234567890abcdef1234"
        assert lines[0].file_path == "app.py"
        assert lines[0].line_number == 1
        assert lines[0].origin_timestamp == "2025-01-01T00:00:00Z"
        assert lines[1].origin_revision == "def4567890abcdef1234567890abcdef1234567"
        assert lines[1].line_number == 2
        assert lines[1].origin_timestamp == "2025-01-02T00:00:00Z"

    def test_parse_empty_output(self):
        lines = parse_blame_porcelain("")
        assert lines == []

    def test_parse_rename_tracking(self):
        lines = parse_blame_porcelain(RENAME_OUTPUT)
        assert len(lines) == 1
        assert lines[0].origin_revision == "abc1234567890abcdef1234567890abcdef1234"
        assert lines[0].file_path == "app.py"
        assert lines[0].line_number == 5


class TestRunGitBlame:
    def test_successful_blame(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = PORCELAIN_OUTPUT
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            lines = run_git_blame("/repo", "app.py")
            assert len(lines) == 2
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "git"
            assert args[1] == "blame"
            assert args[2] == "--porcelain"
            assert "app.py" in args

    def test_blame_nonzero_exit(self):
        mock_result = MagicMock()
        mock_result.returncode = 128
        mock_result.stdout = ""
        mock_result.stderr = "fatal: no such path"
        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(GitBlameError, match="git blame failed"):
                run_git_blame("/repo", "nonexistent.py")

    def test_blame_file_not_found(self):
        with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
            with pytest.raises(GitBlameError, match="Git executable not found"):
                run_git_blame("/repo", "app.py")

    def test_blame_with_whitespace_flag(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = PORCELAIN_OUTPUT
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_git_blame("/repo", "app.py", ignore_whitespace=True)
            args = mock_run.call_args[0][0]
            assert "-w" in args

    def test_blame_with_rename_detection(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = PORCELAIN_OUTPUT
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_git_blame("/repo", "app.py", rename_detection="aggressive")
            args = mock_run.call_args[0][0]
            assert "-C" in args

    def test_blame_with_line_range(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = PORCELAIN_OUTPUT
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_git_blame("/repo", "app.py", start_line=1, end_line=10)
            args = mock_run.call_args[0][0]
            assert "-L" in args
            assert "1,10" in args


class TestRunGitBlameOnFiles:
    def test_blame_multiple_files(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = PORCELAIN_OUTPUT
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            lines = run_git_blame_on_files("/repo", ["app.py", "utils.py"])
            assert len(lines) == 4
            files = {l.file_path for l in lines}
            assert files == {"app.py", "utils.py"}

    def test_blame_one_file_fails_continues(self):
        success = MagicMock()
        success.returncode = 0
        success.stdout = PORCELAIN_OUTPUT
        success.stderr = ""
        failure = MagicMock()
        failure.returncode = 128
        failure.stdout = ""
        failure.stderr = "fatal: no such path"
        with patch("subprocess.run", side_effect=[success, failure]):
            lines = run_git_blame_on_files("/repo", ["app.py", "bad.py"])
            assert len(lines) == 2


class TestIsoFromUnix:
    def test_convert_unix_to_iso(self):
        result = iso_from_unix(1735689600)
        assert result == "2025-01-01T00:00:00Z"

    def test_convert_zero_timestamp(self):
        result = iso_from_unix(0)
        assert result == "1970-01-01T00:00:00Z"
