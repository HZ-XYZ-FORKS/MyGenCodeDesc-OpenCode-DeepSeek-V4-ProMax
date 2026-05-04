from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from aggregateGenCodeDesc.models import (
    DetailAddEntry,
    DetailDeleteEntry,
    DetailFileV2604,
    Blame,
    LineRange,
    GenCodeDescV2604,
)
from aggregateGenCodeDesc.metrics import AllMetrics, compute_all_metrics


@dataclass(slots=True)
class SurvivingLine:
    blame_revision_id: str = ""
    original_file_path: str = ""
    original_line: int = 0
    gen_ratio: int = 0
    gen_method: str = ""
    blame_timestamp: str = ""
    file_name: str = ""
    line_location: int = 0


@dataclass
class AlgCResult:
    surviving_lines: List[SurvivingLine]
    metrics: AllMetrics
    warnings: List[str]


def _make_blame_key(rev_id: str, file_path: str, line: int) -> tuple:
    return (rev_id, file_path, line)


def _make_position_key(file_name: str, line_location: int) -> tuple:
    return (file_name, line_location)


def _expand_line_range(from_: int, to_: int) -> List[int]:
    return list(range(from_, to_ + 1))


import logging
_log = logging.getLogger("aggregateGenCodeDesc")


def accumulate_surviving_set(
    records: List[GenCodeDescV2604],
    end_time: str,
    return_warnings: bool = False,
) -> List[SurvivingLine] | Tuple[List[SurvivingLine], List[str]]:
    warnings: List[str] = []

    if not records:
        if return_warnings:
            return [], warnings
        return []

    sorted_records = sorted(records, key=lambda r: r.REPOSITORY.revisionTimestamp)

    surviving: Dict[str, SurvivingLine] = {}
    position_index: Dict[str, str] = {}

    for record in sorted_records:
        if record.REPOSITORY.revisionTimestamp > end_time:
            continue

        add_count = 0
        for df in record.DETAIL:
            for entry in (df.codeLines or []) + (df.docLines or []):
                if isinstance(entry, DetailAddEntry):
                    if entry.lineRange:
                        add_count += len(_expand_line_range(entry.lineRange.from_, entry.lineRange.to_))
                    elif entry.lineLocation is not None:
                        add_count += 1
        if record.SUMMARY.totalCodeLines > 0 and add_count != record.SUMMARY.totalCodeLines:
            warnings.append(
                f"SUMMARY mismatch for revision {record.REPOSITORY.revisionId}: "
                f"expected totalCodeLines={record.SUMMARY.totalCodeLines}, "
                f"found {add_count} add entries in DETAIL"
            )

        for df in record.DETAIL:
            for entry in df.codeLines:
                if isinstance(entry, DetailDeleteEntry):
                    blame = entry.blame
                    if blame.originalLineRange:
                        for line in _expand_line_range(
                            blame.originalLineRange.from_,
                            blame.originalLineRange.to_,
                        ):
                            blame_key = _make_blame_key(
                                blame.revisionId,
                                blame.originalFilePath,
                                line,
                            )
                            if blame_key in surviving:
                                sl = surviving[blame_key]
                                pos_key = _make_position_key(sl.file_name, sl.line_location)
                                position_index.pop(pos_key, None)
                                del surviving[blame_key]
                    elif blame.originalLine is not None:
                        blame_key = _make_blame_key(
                            blame.revisionId,
                            blame.originalFilePath,
                            blame.originalLine,
                        )
                        if blame_key in surviving:
                            sl = surviving[blame_key]
                            pos_key = _make_position_key(sl.file_name, sl.line_location)
                            position_index.pop(pos_key, None)
                            del surviving[blame_key]

            for entry in df.codeLines:
                if isinstance(entry, DetailAddEntry):
                    blame = entry.blame
                    if entry.lineRange:
                        lines_to_add = _expand_line_range(
                            entry.lineRange.from_,
                            entry.lineRange.to_,
                        )
                        orig_start = blame.originalLine if blame.originalLine else entry.lineRange.from_
                        for i, line_idx in enumerate(lines_to_add):
                            blame_key = _make_blame_key(
                                blame.revisionId,
                                blame.originalFilePath,
                                orig_start + i,
                            )
                            pos_key = _make_position_key(df.fileName, line_idx)
                            if pos_key in position_index:
                                old_blame_key = position_index[pos_key]
                                if old_blame_key in surviving:
                                    del surviving[old_blame_key]
                                warnings.append(
                                    f"Position collision: file={df.fileName} line={line_idx} "
                                    f"overwritten by revision {record.REPOSITORY.revisionId}"
                                )
                            if blame_key in surviving:
                                warnings.append(
                                    f"Duplicate add entry for key {blame_key} at revision {record.REPOSITORY.revisionId}"
                                )
                            sl = SurvivingLine(
                                blame_revision_id=blame.revisionId,
                                original_file_path=blame.originalFilePath,
                                original_line=orig_start + i,
                                gen_ratio=entry.genRatio,
                                gen_method=entry.genMethod,
                                blame_timestamp=blame.timestamp or "",
                                file_name=df.fileName,
                                line_location=line_idx,
                            )
                            surviving[blame_key] = sl
                            position_index[pos_key] = blame_key
                    elif entry.lineLocation is not None and blame.originalLine is not None:
                        blame_key = _make_blame_key(
                            blame.revisionId,
                            blame.originalFilePath,
                            blame.originalLine,
                        )
                        pos_key = _make_position_key(df.fileName, entry.lineLocation)
                        if pos_key in position_index:
                            old_blame_key = position_index[pos_key]
                            if old_blame_key in surviving:
                                del surviving[old_blame_key]
                            warnings.append(
                                f"Position collision: file={df.fileName} line={entry.lineLocation} "
                                f"overwritten by revision {record.REPOSITORY.revisionId}"
                            )
                        if blame_key in surviving:
                            warnings.append(
                                f"Duplicate add entry for key {blame_key} at revision {record.REPOSITORY.revisionId}"
                            )
                        sl = SurvivingLine(
                            blame_revision_id=blame.revisionId,
                            original_file_path=blame.originalFilePath,
                            original_line=blame.originalLine,
                            gen_ratio=entry.genRatio,
                            gen_method=entry.genMethod,
                            blame_timestamp=blame.timestamp or "",
                            file_name=df.fileName,
                            line_location=entry.lineLocation,
                        )
                        surviving[blame_key] = sl
                        position_index[pos_key] = blame_key

    result = list(surviving.values())
    if return_warnings:
        return result, warnings
    return result


def compute_alg_c_metrics(
    records: List[GenCodeDescV2604],
    start_time: str,
    end_time: str,
    threshold: int,
) -> AlgCResult:
    surviving, warnings = accumulate_surviving_set(records, end_time, return_warnings=True)

    in_window = [
        s for s in surviving
        if start_time <= s.blame_timestamp <= end_time
    ]

    gen_ratios = [s.gen_ratio for s in in_window]
    metrics = compute_all_metrics(gen_ratios, threshold)

    return AlgCResult(
        surviving_lines=in_window,
        metrics=metrics,
        warnings=warnings,
    )


def stream_accumulate_surviving_set(
    gencode_dir: str,
    end_time: str,
    return_warnings: bool = False,
) -> List[SurvivingLine] | Tuple[List[SurvivingLine], List[str]]:
    import json as _json
    import json as _json_module
    try:
        import orjson as _fast_json
        _use_fast = True
    except ImportError:
        _use_fast = False

    from pathlib import Path

    warnings: List[str] = []
    path = Path(gencode_dir)

    file_info: List[Tuple[str, Path]] = []
    for jf in sorted(path.glob("*.json")):
        try:
            if _use_fast:
                with open(jf, "rb") as f:
                    data = _fast_json.loads(f.read())
            else:
                with open(jf, "r", encoding="utf-8") as f:
                    data = _json.load(f)
            ts = data.get("REPOSITORY", {}).get("revisionTimestamp", "")
            file_info.append((ts, jf))
        except (_json.JSONDecodeError, KeyError, OSError) as e:
            warnings.append(f"Skipping unreadable file {jf.name}: {e}")

    file_info.sort(key=lambda x: x[0])

    surviving: Dict[str, SurvivingLine] = {}
    position_index: Dict[str, str] = {}

    for ts, jf in file_info:
        if ts > end_time:
            continue
        try:
            if _use_fast:
                with open(jf, "rb") as f:
                    data = _fast_json.loads(f.read())
            else:
                with open(jf, "r", encoding="utf-8") as f:
                    data = _json.load(f)
        except (_json.JSONDecodeError, OSError) as e:
            warnings.append(f"I/O error reading {jf.name}: {e}")
            continue

        details = data.get("DETAIL", [])
        if not details:
            continue

        add_count = 0
        for df_data in details:
            for entry in df_data.get("codeLines", []) + df_data.get("docLines", []):
                if entry.get("changeType") == "add":
                    if "lineRange" in entry:
                        rng = entry["lineRange"]
                        add_count += rng["to"] - rng["from"] + 1
                    elif "lineLocation" in entry:
                        add_count += 1

        summary = data.get("SUMMARY", {})
        total_code = summary.get("totalCodeLines", 0)
        rev_id = data.get("REPOSITORY", {}).get("revisionId", "?")
        if total_code > 0 and add_count != total_code:
            warnings.append(
                f"SUMMARY mismatch for revision {rev_id}: "
                f"expected totalCodeLines={total_code}, found {add_count} add entries"
            )
        _log.info("LOAD rev=%s entries=%d", rev_id, add_count)

        for df_data in details:
            file_name = df_data.get("fileName", "")
            for entry in df_data.get("codeLines", []) + df_data.get("docLines", []):
                change_type = entry.get("changeType", "")
                blame_data = entry.get("blame", {})

                if change_type == "delete":
                    _log.info("PROCESS file=%s line=%s state=DELETED origin=%s",
                              file_name, blame_data.get("originalLine", "?"),
                              blame_data.get("revisionId", "?"),
                              extra={"phase": "PROCESS"})
                    if "originalLineRange" in blame_data:
                        rng = blame_data["originalLineRange"]
                        for line in range(rng["from"], rng["to"] + 1):
                            key = _make_blame_key(
                                blame_data.get("revisionId", ""),
                                blame_data.get("originalFilePath", ""),
                                line,
                            )
                            if key in surviving:
                                sl = surviving[key]
                                pos_key = _make_position_key(sl.file_name, sl.line_location)
                                position_index.pop(pos_key, None)
                                del surviving[key]
                    else:
                        key = _make_blame_key(
                            blame_data.get("revisionId", ""),
                            blame_data.get("originalFilePath", ""),
                            blame_data.get("originalLine", 0),
                        )
                        if key in surviving:
                            sl = surviving[key]
                            pos_key = _make_position_key(sl.file_name, sl.line_location)
                            position_index.pop(pos_key, None)
                            del surviving[key]

                elif change_type == "add":
                    _log.info("PROCESS file=%s line=%s state=ADDED origin=%s genRatio=%s",
                              file_name,
                              entry.get("lineLocation", entry.get("lineRange", {}).get("from", "?")),
                              blame_data.get("revisionId", "?"),
                              entry.get("genRatio", 0),
                              extra={"phase": "PROCESS"})
                    gen_ratio = entry.get("genRatio", 0)
                    gen_method = entry.get("genMethod", "Manual")
                    if "lineRange" in entry:
                        rng = entry["lineRange"]
                        orig_line = blame_data.get("originalLine", rng["from"])
                        for i, line_idx in enumerate(range(rng["from"], rng["to"] + 1)):
                            blame_key = _make_blame_key(
                                blame_data.get("revisionId", ""),
                                blame_data.get("originalFilePath", file_name),
                                orig_line + i,
                            )
                            pos_key = _make_position_key(file_name, line_idx)
                            if pos_key in position_index:
                                old_key = position_index[pos_key]
                                if old_key in surviving:
                                    del surviving[old_key]
                                warnings.append(
                                    f"Position collision: file={file_name} line={line_idx}"
                                )
                            sl = SurvivingLine(
                                blame_revision_id=blame_data.get("revisionId", ""),
                                original_file_path=blame_data.get("originalFilePath", file_name),
                                original_line=orig_line + i,
                                gen_ratio=gen_ratio,
                                gen_method=gen_method,
                                blame_timestamp=blame_data.get("timestamp", ""),
                                file_name=file_name,
                                line_location=line_idx,
                            )
                            surviving[blame_key] = sl
                            position_index[pos_key] = blame_key
                    elif "lineLocation" in entry:
                        line_loc = entry["lineLocation"]
                        orig_line = blame_data.get("originalLine", line_loc)
                        blame_key = _make_blame_key(
                            blame_data.get("revisionId", ""),
                            blame_data.get("originalFilePath", file_name),
                            orig_line,
                        )
                        pos_key = _make_position_key(file_name, line_loc)
                        if pos_key in position_index:
                            old_key = position_index[pos_key]
                            if old_key in surviving:
                                del surviving[old_key]
                            warnings.append(
                                f"Position collision: file={file_name} line={line_loc}"
                            )
                        sl = SurvivingLine(
                            blame_revision_id=blame_data.get("revisionId", ""),
                            original_file_path=blame_data.get("originalFilePath", file_name),
                            original_line=orig_line,
                            gen_ratio=gen_ratio,
                            gen_method=gen_method,
                            blame_timestamp=blame_data.get("timestamp", ""),
                            file_name=file_name,
                            line_location=line_loc,
                        )
                        surviving[blame_key] = sl
                        position_index[pos_key] = blame_key

    result = list(surviving.values())
    if return_warnings:
        return result, warnings
    return result
