import subprocess
from datetime import datetime, timezone
from typing import List, Optional

from aggregateGenCodeDesc.alg_a import BlameLine


class GitBlameError(Exception):
    pass


class SvnBlameError(Exception):
    pass


def iso_from_unix(unix_ts: int) -> str:
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_blame_porcelain(output: str) -> List[BlameLine]:
    if not output.strip():
        return []

    lines = output.split("\n")
    result = []
    current_revision = ""
    current_orig_line = 0
    current_final_line = 0
    current_timestamp = ""
    current_filename = ""

    for line in lines:
        if not line:
            continue

        if line.startswith("\t"):
            if current_revision and current_filename:
                result.append(BlameLine(
                    blame=f"{current_revision} {current_filename} {current_final_line}",
                    origin_revision=current_revision,
                    file_path=current_filename,
                    line_number=current_final_line,
                    origin_timestamp=current_timestamp,
                    origin_line=current_orig_line,
                    origin_file_path=current_filename,
                ))
                current_final_line += 1
                current_orig_line += 1
            continue

        if not line[0].isspace() and len(line) >= 7:
            parts = line.split()
            if len(parts) >= 3 and len(parts[0]) >= 7 and all(c in "0123456789abcdef" for c in parts[0]):
                current_revision = parts[0]
                try:
                    current_orig_line = int(parts[1])
                    current_final_line = int(parts[2])
                except (IndexError, ValueError):
                    pass
                continue

        if line.startswith("author-time "):
            try:
                unix_ts = int(line.split()[1])
                current_timestamp = iso_from_unix(unix_ts)
            except (IndexError, ValueError):
                pass

        elif line.startswith("filename "):
            current_filename = line[len("filename "):]

    return result


def run_git_blame(
    repo_path: str,
    file_path: str,
    ignore_whitespace: bool = False,
    rename_detection: str = "basic",
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
) -> List[BlameLine]:
    cmd = ["git", "blame", "--porcelain"]

    if ignore_whitespace:
        cmd.append("-w")

    if rename_detection == "aggressive":
        cmd.extend(["-M", "-C", "-C"])
    elif rename_detection == "basic":
        cmd.append("-M")

    if start_line is not None and end_line is not None:
        cmd.extend(["-L", f"{start_line},{end_line}"])

    cmd.append(file_path)

    try:
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except FileNotFoundError:
        raise GitBlameError("Git executable not found. Ensure git is installed and on PATH.")

    if result.returncode != 0:
        raise GitBlameError(
            f"git blame failed (exit {result.returncode}) for {file_path}: {result.stderr.strip()}"
        )

    lines = parse_blame_porcelain(result.stdout)
    for l in lines:
        l.file_path = file_path

    import logging
    logging.getLogger("aggregateGenCodeDesc").info("LOAD blame file=%s lines=%d", file_path, len(lines))

    return lines


def run_git_blame_on_files(
    repo_path: str,
    file_paths: List[str],
    ignore_whitespace: bool = False,
    rename_detection: str = "basic",
) -> List[BlameLine]:
    all_lines = []
    for fp in file_paths:
        try:
            lines = run_git_blame(
                repo_path, fp,
                ignore_whitespace=ignore_whitespace,
                rename_detection=rename_detection,
            )
            all_lines.extend(lines)
        except GitBlameError:
            pass
    return all_lines


def parse_svn_blame(output: str) -> List[BlameLine]:
    if not output.strip():
        return []

    lines = output.split("\n")
    result = []
    for line in lines:
        if not line.strip():
            continue
        stripped = line.rstrip("\n")
        if len(stripped) < 8:
            continue
        try:
            rev_part = stripped[:8].strip()
            revision = str(int(rev_part))
            ln = len(result) + 1
            result.append(BlameLine(
                blame=f"{revision}",
                origin_revision=revision,
                file_path="",
                line_number=ln,
                origin_timestamp="",
                origin_line=ln,
                origin_file_path="",
            ))
        except (ValueError, IndexError):
            continue
    return result


def _resolve_svn_timestamps(repo_url: str, revisions: set) -> dict:
    timestamps = {}
    for rev in sorted(revisions):
        try:
            log = subprocess.run(
                ["svn", "log", "-r", str(rev), "--xml", repo_url],
                capture_output=True, text=True, timeout=60,
            )
            if log.returncode == 0 and "<date>" in log.stdout:
                date_str = log.stdout.split("<date>")[1].split("</date>")[0]
                dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                timestamps[rev] = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            pass
    return timestamps


def run_svn_blame(
    repo_url: str,
    file_path: str,
) -> List[BlameLine]:
    cmd = ["svn", "blame", "--non-interactive", f"{repo_url}/{file_path}"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except FileNotFoundError:
        raise SvnBlameError("SVN executable not found. Ensure svn is installed and on PATH.")

    if result.returncode != 0:
        raise SvnBlameError(
            f"svn blame failed (exit {result.returncode}) for {file_path}: {result.stderr.strip()}"
        )

    lines = parse_svn_blame(result.stdout)
    for l in lines:
        l.file_path = file_path

    revisions = {l.origin_revision for l in lines}
    timestamps = _resolve_svn_timestamps(repo_url, revisions)
    for l in lines:
        if l.origin_revision in timestamps:
            l.origin_timestamp = timestamps[l.origin_revision]

    import logging
    logging.getLogger("aggregateGenCodeDesc").info("LOAD blame file=%s lines=%d", file_path, len(lines))

    return lines
