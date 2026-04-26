import subprocess
import pytest
from unittest.mock import patch, MagicMock, mock_open

from aggregateGenCodeDesc.vcs_ordering import (
    get_git_commit_order,
    get_ordered_patch_sequence,
    CommitOrderError,
    load_ordered_patches,
)


GIT_LOG_OUTPUT = """abc123
def456
ghi789
"""

GIT_LOG_WITH_TIMESTAMPS = """abc123 1700000000
def456 1700086400
ghi789 1700172800
"""


class TestGetGitCommitOrder:
    def test_get_topological_order(self):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = GIT_LOG_OUTPUT
        mock.stderr = ""
        with patch("subprocess.run", return_value=mock) as m:
            commits = get_git_commit_order("/repo", "main")
            assert commits == ["abc123", "def456", "ghi789"]
            m.assert_called_once()

    def test_get_order_with_start_end_time(self):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "abc123\ndef456\n"
        mock.stderr = ""
        with patch("subprocess.run", return_value=mock) as m:
            commits = get_git_commit_order(
                "/repo", "main",
                start_time="2026-01-01T00:00:00Z",
                end_time="2026-03-01T00:00:00Z",
            )
            assert len(commits) == 2
            args = m.call_args[0][0]
            assert any(a.startswith("--after") for a in args)
            assert any(a.startswith("--before") for a in args)

    def test_git_not_found(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(CommitOrderError, match="Git executable not found"):
                get_git_commit_order("/repo", "main")

    def test_git_error_exit(self):
        mock = MagicMock()
        mock.returncode = 128
        mock.stderr = "fatal: not a git repository"
        mock.stdout = ""
        with patch("subprocess.run", return_value=mock):
            with pytest.raises(CommitOrderError, match="not a git repository"):
                get_git_commit_order("/bad", "main")


class TestLoadOrderedPatches:
    def test_load_patches_from_dir(self, tmp_path):
        patch_dir = tmp_path / "patches"
        patch_dir.mkdir()
        (patch_dir / "abc123.patch").write_text("diff --git a/f b/f\n+line1\n")
        (patch_dir / "def456.patch").write_text("diff --git a/f b/f\n+line2\n")
        (patch_dir / "ghi789.patch").write_text("diff --git a/f b/f\n+line3\n")

        ordered_commits = ["abc123", "def456", "ghi789"]
        seq = load_ordered_patches(str(patch_dir), ordered_commits)
        assert len(seq) == 3
        assert seq[0][0] == "diff --git a/f b/f\n+line1\n"
        assert seq[0][1] == "abc123"
        assert seq[2][0] == "diff --git a/f b/f\n+line3\n"
        assert seq[2][1] == "ghi789"

    def test_missing_patch_raises(self, tmp_path):
        patch_dir = tmp_path / "patches"
        patch_dir.mkdir()
        (patch_dir / "abc123.patch").write_text("+line1\n")

        ordered_commits = ["abc123", "def456"]
        with pytest.raises(CommitOrderError, match="Missing patch"):
            load_ordered_patches(str(patch_dir), ordered_commits)

    def test_extra_patches_in_dir_ignored(self, tmp_path):
        patch_dir = tmp_path / "patches"
        patch_dir.mkdir()
        (patch_dir / "abc123.patch").write_text("+line1\n")
        (patch_dir / "extra.patch").write_text("+extra\n")

        ordered_commits = ["abc123"]
        seq = load_ordered_patches(str(patch_dir), ordered_commits)
        assert len(seq) == 1


class TestGetOrderedPatchSequence:
    def test_full_pipeline(self, tmp_path):
        patch_dir = tmp_path / "patches"
        patch_dir.mkdir()
        (patch_dir / "abc123.patch").write_text("diff --git a/f b/f\n+line1\n")
        (patch_dir / "def456.patch").write_text("diff --git a/f b/f\n+line2\n")

        log_mock = MagicMock()
        log_mock.returncode = 0
        log_mock.stdout = "abc123\ndef456\n"
        log_mock.stderr = ""
        with patch("subprocess.run", return_value=log_mock):
            seq = get_ordered_patch_sequence(
                repo_path="/repo",
                repo_branch="main",
                commit_patch_dir=str(patch_dir),
            )
            assert len(seq) == 2
            assert seq[0][1] == "abc123"
