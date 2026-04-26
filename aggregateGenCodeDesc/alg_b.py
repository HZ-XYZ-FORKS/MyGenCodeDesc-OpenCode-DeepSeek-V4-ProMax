import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, OrderedDict, Tuple

from aggregateGenCodeDesc.models import GenCodeDescV2603
from aggregateGenCodeDesc.alg_a import (
    BlameLine,
    build_line_to_genratio_map,
    compute_alg_a_metrics,
    AlgAResult,
)


@dataclass
class LineEntry:
    origin_revision: str = ""
    origin_timestamp: str = ""
    gen_ratio: int = 0


@dataclass
class FileLineTracker:
    lines: Dict[str, Dict[int, LineEntry]] = field(default_factory=dict)

    def add_line(self, file_path: str, line_num: int, revision: str, timestamp: str) -> None:
        if file_path not in self.lines:
            self.lines[file_path] = {}
        self.lines[file_path][line_num] = LineEntry(
            origin_revision=revision,
            origin_timestamp=timestamp,
        )

    def _shift_lines_after(self, file_path: str, after_line: int, delta: int) -> None:
        if file_path not in self.lines:
            return
        if delta == 0:
            return
        old = self.lines[file_path]
        new: Dict[int, LineEntry] = {}
        for ln, entry in old.items():
            if ln <= after_line:
                new[ln] = entry
            else:
                new[ln + delta] = entry
        self.lines[file_path] = new

    def delete_line_at(self, file_path: str, line_num: int) -> None:
        if file_path not in self.lines:
            return
        old = self.lines[file_path]
        if line_num in old:
            del old[line_num]
        new: Dict[int, LineEntry] = {}
        for ln, entry in old.items():
            if ln < line_num:
                new[ln] = entry
            else:
                new[ln - 1] = entry
        self.lines[file_path] = new

    def delete_line_range(self, file_path: str, old_start: int, old_count: int) -> None:
        for _ in range(old_count):
            self.delete_line_at(file_path, old_start)

    def rename_file(self, old_path: str, new_path: str) -> None:
        if old_path in self.lines:
            self.lines[new_path] = self.lines.pop(old_path)

    def to_blame_lines(self) -> List[BlameLine]:
        result = []
        for file_path, line_map in self.lines.items():
            for line_num, entry in sorted(line_map.items()):
                result.append(BlameLine(
                    blame=f"{entry.origin_revision} {file_path} {line_num}",
                    origin_revision=entry.origin_revision,
                    file_path=file_path,
                    line_number=line_num,
                    origin_timestamp=entry.origin_timestamp,
                    gen_ratio=entry.gen_ratio,
                ))
        return result


@dataclass
class DiffHunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[str] = field(default_factory=list)


@dataclass
class DiffFile:
    old_file: str
    new_file: str
    is_rename: bool = False
    is_new: bool = False
    is_delete: bool = False
    hunks: List[DiffHunk] = field(default_factory=list)


HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)")


def parse_unified_diff(diff_text: str) -> List[DiffFile]:
    if not diff_text.strip():
        return []

    files = []
    current_file: Optional[DiffFile] = None
    current_hunk: Optional[DiffHunk] = None

    for line in diff_text.split("\n"):
        if line.startswith("diff --git "):
            if current_file:
                files.append(current_file)
            parts = line[len("diff --git "):].split()
            old = parts[0] if parts else ""
            new = parts[1] if len(parts) > 1 else old
            current_file = DiffFile(old_file=old, new_file=new)
            current_hunk = None

        elif line.startswith("rename from "):
            if current_file:
                current_file.is_rename = True

        elif line.startswith("--- ") and current_file:
            path_part = line[4:]
            if path_part.startswith("a/") or path_part.startswith("b/"):
                current_file.old_file = path_part

        elif line.startswith("+++ ") and current_file:
            path_part = line[4:]
            if path_part.startswith("a/") or path_part.startswith("b/"):
                current_file.new_file = path_part

        elif line.startswith("@@") and current_file:
            m = HUNK_HEADER_RE.match(line)
            if m:
                old_start = int(m.group(1))
                old_cnt = int(m.group(2)) if m.group(2) else 1
                new_start = int(m.group(3))
                new_cnt = int(m.group(4)) if m.group(4) else 1
                current_hunk = DiffHunk(
                    old_start=old_start, old_count=old_cnt,
                    new_start=new_start, new_count=new_cnt,
                )
                current_file.hunks.append(current_hunk)

        elif current_hunk is not None:
            if line:
                current_hunk.lines.append(line)

    if current_file and (current_file.hunks or current_file.is_rename):
        files.append(current_file)

    return files


def _insert_line_at(file_path: str, line_num: int, tracker: FileLineTracker, revision: str, timestamp: str) -> None:
    if file_path not in tracker.lines:
        tracker.lines[file_path] = {}
    old = tracker.lines[file_path]
    new: Dict[int, LineEntry] = {}
    for ln, entry in old.items():
        if ln < line_num:
            new[ln] = entry
        else:
            new[ln + 1] = entry
    new[line_num] = LineEntry(origin_revision=revision, origin_timestamp=timestamp)
    tracker.lines[file_path] = new


def replay_diff(
    files: List[DiffFile],
    revision: str,
    timestamp: str,
    tracker: Optional[FileLineTracker] = None,
) -> FileLineTracker:
    if tracker is None:
        tracker = FileLineTracker()

    for df in files:
        old_path = df.old_file
        new_path = df.new_file

        if df.is_rename and not df.hunks:
            tracker.rename_file(old_path, new_path)
            continue

        for hunk in df.hunks:
            ol = hunk.old_start
            nl = hunk.new_start

            for ln_text in hunk.lines:
                if ln_text.startswith("-"):
                    tracker.delete_line_at(old_path, ol)
                elif ln_text.startswith("+"):
                    _insert_line_at(new_path, nl, tracker, revision, timestamp)
                    nl += 1
                else:
                    ol += 1
                    nl += 1

    return tracker


def old_count_from_hunk(hunk: DiffHunk) -> int:
    return sum(1 for ln in hunk.lines if ln.startswith("-") or ln.startswith(" "))


def old_count_from_lines(lines: List[str]) -> int:
    return sum(1 for ln in lines if ln.startswith("-") or ln.startswith(" "))


def delete_count_from_lines(lines: List[str]) -> int:
    return sum(1 for ln in lines if ln.startswith("-"))


def compute_alg_b_metrics(
    diff_sequence: List[Tuple[str, str, str]],
    gencode_records: List[GenCodeDescV2603],
    start_time: str,
    end_time: str,
    threshold: int,
) -> AlgAResult:
    tracker = FileLineTracker()
    for diff_text, revision, timestamp in diff_sequence:
        files = parse_unified_diff(diff_text)
        tracker = replay_diff(files, revision, timestamp, tracker)

    blame_lines = tracker.to_blame_lines()
    genratio_map = build_line_to_genratio_map(gencode_records)
    return compute_alg_a_metrics(blame_lines, genratio_map, start_time, end_time, threshold)
