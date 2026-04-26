from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from aggregateGenCodeDesc.models import (
    DetailFileV2603,
    GenCodeDescV2603,
    LineLocation,
    LineRange,
)
from aggregateGenCodeDesc.metrics import AllMetrics, compute_all_metrics


@dataclass
class BlameLine:
    blame: str
    origin_revision: str
    file_path: str
    line_number: int
    origin_timestamp: str
    gen_ratio: int = 0
    gen_method: str = "Manual"


@dataclass
class AlgAResult:
    in_window_lines: List[BlameLine]
    out_of_window_lines: List[BlameLine]
    metrics: AllMetrics


def build_line_to_genratio_map(
    records: List[GenCodeDescV2603],
) -> Dict[Tuple[str, str, int], int]:
    m: Dict[Tuple[str, str, int], int] = {}
    for record in records:
        rev_id = record.REPOSITORY.revisionId
        for df in record.DETAIL:
            for entry in (df.codeLines or []):
                if isinstance(entry, LineLocation):
                    m[(rev_id, df.fileName, entry.lineLocation)] = entry.genRatio
                elif isinstance(entry, LineRange):
                    for ln in range(entry.from_, entry.to_ + 1):
                        m[(rev_id, df.fileName, ln)] = entry.genRatio
            for entry in (df.docLines or []):
                if isinstance(entry, LineLocation):
                    m[(rev_id, df.fileName, entry.lineLocation)] = entry.genRatio
                elif isinstance(entry, LineRange):
                    for ln in range(entry.from_, entry.to_ + 1):
                        m[(rev_id, df.fileName, ln)] = entry.genRatio
    return m


def mark_window_lines(
    blame_lines: List[BlameLine],
    start_time: str,
    end_time: str,
) -> Tuple[List[BlameLine], List[BlameLine]]:
    in_window = []
    out_of_window = []
    for line in blame_lines:
        if start_time <= line.origin_timestamp <= end_time:
            in_window.append(line)
        else:
            out_of_window.append(line)
    return in_window, out_of_window


def resolve_gen_ratios_from_v2603(
    in_window_lines: List[BlameLine],
    genratio_map: Dict[Tuple[str, str, int], int],
) -> List[int]:
    gen_ratios = []
    for line in in_window_lines:
        key = (line.origin_revision, line.file_path, line.line_number)
        gr = genratio_map.get(key, 0)
        line.gen_ratio = gr
        if gr == 0:
            line.gen_method = "Manual"
        gen_ratios.append(gr)
    return gen_ratios


def compute_alg_a_metrics(
    blame_lines: List[BlameLine],
    genratio_map: Dict[Tuple[str, str, int], int],
    start_time: str,
    end_time: str,
    threshold: int,
) -> AlgAResult:
    in_window, out_of_window = mark_window_lines(blame_lines, start_time, end_time)
    gen_ratios = resolve_gen_ratios_from_v2603(in_window, genratio_map)
    metrics = compute_all_metrics(gen_ratios, threshold)
    return AlgAResult(
        in_window_lines=in_window,
        out_of_window_lines=out_of_window,
        metrics=metrics,
    )
