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


@dataclass
class SurvivingLine:
    blame_revision_id: str
    original_file_path: str
    original_line: int
    gen_ratio: int
    gen_method: str
    blame_timestamp: str
    file_name: str = ""
    line_location: int = 0


@dataclass
class AlgCResult:
    surviving_lines: List[SurvivingLine]
    metrics: AllMetrics
    warnings: List[str]


def _make_blame_key(rev_id: str, file_path: str, line: int) -> str:
    return f"{rev_id}::{file_path}::{line}"


def _make_position_key(file_name: str, line_location: int) -> str:
    return f"{file_name}::{line_location}"


def _expand_line_range(from_: int, to_: int) -> List[int]:
    return list(range(from_, to_ + 1))


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
