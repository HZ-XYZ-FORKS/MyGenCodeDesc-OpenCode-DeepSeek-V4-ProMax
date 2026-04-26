from typing import Any, Dict, List

from aggregateGenCodeDesc.models import DetailFileV2603, LineLocation, LineRange
from aggregateGenCodeDesc.metrics import AllMetrics


AGGREGATE_OUTPUT_FILENAME = "genCodeDescV26.03.json"
PATCH_OUTPUT_FILENAME = "commitStart2EndTime.patch"


def _line_entry_to_dict(entry) -> Dict[str, Any]:
    if isinstance(entry, LineLocation):
        return {
            "lineLocation": entry.lineLocation,
            "genRatio": entry.genRatio,
            "genMethod": entry.genMethod,
        }
    if isinstance(entry, LineRange):
        return {
            "lineRange": {"from": entry.from_, "to": entry.to_},
            "genRatio": entry.genRatio,
            "genMethod": entry.genMethod,
        }
    return {}


def build_aggregate_output(
    repo_url: str,
    repo_branch: str,
    start_time: str,
    end_time: str,
    algorithm: str,
    scope: str,
    threshold: int,
    input_protocol_version: str,
    metrics: AllMetrics,
    warnings: List[str],
    detail_files: List[DetailFileV2603],
    vcs_type: str = "git",
    gen_ratios: List[int] | None = None,
) -> Dict[str, Any]:
    if gen_ratios is None:
        gen_ratios = []

    total_code = len(gen_ratios)
    full_gen = sum(1 for r in gen_ratios if r == 100)
    partial_gen = sum(1 for r in gen_ratios if 0 < r < 100)
    total_doc = 0
    full_gen_doc = 0
    partial_gen_doc = 0

    detail_output = []
    for df in detail_files:
        file_out: Dict[str, Any] = {"fileName": df.fileName}
        if df.codeLines:
            file_out["codeLines"] = [_line_entry_to_dict(e) for e in df.codeLines]
        if df.docLines:
            file_out["docLines"] = [_line_entry_to_dict(e) for e in df.docLines]
        if df.codeLines or df.docLines:
            detail_output.append(file_out)

    return {
        "protocolName": "generatedTextDesc",
        "protocolVersion": "26.03",
        "codeAgent": "aggregateGenCodeDesc",
        "SUMMARY": {
            "totalCodeLines": total_code,
            "fullGeneratedCodeLines": full_gen,
            "partialGeneratedCodeLines": partial_gen,
            "totalDocLines": total_doc,
            "fullGeneratedDocLines": full_gen_doc,
            "partialGeneratedDocLines": partial_gen_doc,
        },
        "DETAIL": detail_output,
        "REPOSITORY": {
            "vcsType": vcs_type,
            "repoURL": repo_url,
            "repoBranch": repo_branch,
            "revisionId": f"aggregate:{start_time}..{end_time}",
        },
        "AGGREGATE": {
            "window": {
                "startTime": start_time,
                "endTime": end_time,
            },
            "parameters": {
                "algorithm": algorithm,
                "scope": scope,
                "threshold": threshold,
                "inputProtocolVersion": input_protocol_version,
            },
            "metrics": {
                "weighted": {
                    "value": metrics.weighted.value,
                    "numerator": metrics.weighted.numerator,
                },
                "fullyAI": {
                    "value": metrics.fully_ai.value,
                    "numerator": metrics.fully_ai.numerator,
                },
                "mostlyAI": {
                    "value": metrics.mostly_ai.value,
                    "numerator": metrics.mostly_ai.numerator,
                    "threshold": metrics.mostly_ai.threshold,
                },
            },
            "diagnostics": {
                "missingRevisions": [],
                "duplicateRevisions": [],
                "clockSkewDetected": False,
                "warnings": warnings,
            },
        },
    }
