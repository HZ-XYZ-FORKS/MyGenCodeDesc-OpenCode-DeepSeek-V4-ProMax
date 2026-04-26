import pytest

from aggregateGenCodeDesc.models import (
    DetailFileV2603,
    GenCodeDescV2603,
    LineLocation,
    Repository,
    Summary,
)
from aggregateGenCodeDesc.alg_b import (
    parse_unified_diff,
    DiffHunk,
    DiffFile,
    replay_diff,
    FileLineTracker,
    compute_alg_b_metrics,
)


SIMPLE_DIFF = """diff --git a/app.py b/app.py
index 1234567..abcdefg 100644
--- a/app.py
+++ b/app.py
@@ -1,0 +1,3 @@
+line 1
+line 2
+line 3
"""

MULTI_HUNK_DIFF = """diff --git a/app.py b/app.py
index 1234567..abcdefg 100644
--- a/app.py
+++ b/app.py
@@ -1,0 +1,3 @@
+line 1
+line 2
+line 3
@@ -10,3 +13,4 @@
 context line
-removed line
+added line
 context line 2
+added line 2
"""

DELETE_ONLY_DIFF = """diff --git a/app.py b/app.py
index 1234567..abcdefg 100644
--- a/app.py
+++ b/app.py
@@ -1,3 +0,0 @@
-line 1
-line 2
-line 3
"""


RENAME_DIFF = """diff --git a/old.py b/new.py
similarity index 100%
rename from old.py
rename to new.py
"""


class TestParseUnifiedDiff:
    def test_parse_simple_add(self):
        files = parse_unified_diff(SIMPLE_DIFF)
        assert len(files) == 1
        f = files[0]
        assert f.old_file == "a/app.py"
        assert f.new_file == "b/app.py"
        assert len(f.hunks) == 1
        h = f.hunks[0]
        assert h.old_start == 1
        assert h.new_start == 1
        assert len(h.lines) == 3
        assert all(ln.startswith("+") for ln in h.lines)

    def test_parse_multi_hunk(self):
        files = parse_unified_diff(MULTI_HUNK_DIFF)
        assert len(files) == 1
        f = files[0]
        assert len(f.hunks) == 2
        assert f.hunks[0].new_start == 1
        assert f.hunks[1].new_start == 13

    def test_parse_no_diff_content(self):
        files = parse_unified_diff("")
        assert len(files) == 0

    def test_parse_rename(self):
        files = parse_unified_diff(RENAME_DIFF)
        assert len(files) == 1
        f = files[0]
        assert f.old_file == "a/old.py"
        assert f.new_file == "b/new.py"
        assert f.is_rename is True
        assert len(f.hunks) == 0


class TestReplayDiff:
    def test_replay_add_lines(self):
        tracker = FileLineTracker()
        files = parse_unified_diff(SIMPLE_DIFF)
        tracker = replay_diff(files, "abc123", "2026-01-01T00:00:00Z", tracker)
        assert len(tracker.lines["b/app.py"]) == 3
        assert tracker.lines["b/app.py"][1].origin_revision == "abc123"
        assert tracker.lines["b/app.py"][2].origin_revision == "abc123"

    def test_replay_delete_lines(self):
        tracker = FileLineTracker()
        tracker.add_line("a/app.py", 1, "abc123", "2026-01-01T00:00:00Z")
        tracker.add_line("a/app.py", 2, "abc123", "2026-01-01T00:00:00Z")
        tracker.add_line("a/app.py", 3, "abc123", "2026-01-01T00:00:00Z")
        files = parse_unified_diff(DELETE_ONLY_DIFF)
        tracker = replay_diff(files, "def456", "2026-02-01T00:00:00Z", tracker)
        assert "a/app.py" not in tracker.lines or len(tracker.lines["a/app.py"]) == 0

    def test_replay_rename_preserves_lines(self):
        tracker = FileLineTracker()
        tracker.lines["a/old.py"] = {
            1: type('obj', (object,), {'origin_revision': 'abc123', 'gen_ratio': 100})(),
        }
        files = parse_unified_diff(RENAME_DIFF)
        tracker = replay_diff(files, "def456", "2026-02-01T00:00:00Z", tracker)
        assert "b/new.py" in tracker.lines
        assert "a/old.py" not in tracker.lines

    def test_multi_diff_replay_tracks_origin(self):
        tracker = FileLineTracker()
        f1 = parse_unified_diff(SIMPLE_DIFF)
        tracker = replay_diff(f1, "c1", "2026-01-01T00:00:00Z", tracker)
        assert tracker.lines["b/app.py"][1].origin_revision == "c1"

        f2 = parse_unified_diff("""diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -2,2 +2,3 @@
 line 1
+new line after line 1
 line 2
""")
        tracker = replay_diff(f2, "c2", "2026-01-02T00:00:00Z", tracker)
        assert tracker.lines["b/app.py"][3].origin_revision == "c2"
        assert tracker.lines["b/app.py"][4].origin_revision == "c1"


class TestFileLineTracker:
    def test_track_add_line(self):
        tracker = FileLineTracker()
        tracker.add_line("app.py", 1, "c1", "2026-01-01T00:00:00Z")
        assert "app.py" in tracker.lines
        assert tracker.lines["app.py"][1].origin_revision == "c1"

    def test_track_delete_line(self):
        tracker = FileLineTracker()
        tracker.add_line("app.py", 1, "c1", "2026-01-01T00:00:00Z")
        tracker.add_line("app.py", 2, "c1", "2026-01-01T00:00:00Z")
        tracker.delete_line_range("app.py", 1, 2)
        assert len(tracker.lines["app.py"]) == 0

    def test_track_file_rename(self):
        tracker = FileLineTracker()
        tracker.add_line("old.py", 1, "c1", "2026-01-01T00:00:00Z")
        tracker.rename_file("old.py", "new.py")
        assert "old.py" not in tracker.lines
        assert "new.py" in tracker.lines
        assert tracker.lines["new.py"][1].origin_revision == "c1"
