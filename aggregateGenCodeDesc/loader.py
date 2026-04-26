import json
import os
from enum import Enum
from pathlib import Path
from typing import List, Optional, Union

from aggregateGenCodeDesc.models import (
    Blame,
    DetailAddEntry,
    DetailDeleteEntry,
    DetailFileV2603,
    DetailFileV2604,
    GenCodeDescV2603,
    GenCodeDescV2604,
    LineLocation,
    LineRange,
    Repository,
    RepositoryV2604,
    Summary,
    ValidationError,
)


class ProtocolVersion(str, Enum):
    V26_03 = "26.03"
    V26_04 = "26.04"

    @classmethod
    def from_string(cls, s: str) -> "ProtocolVersion":
        if s == cls.V26_03.value:
            return cls.V26_03
        if s == cls.V26_04.value:
            return cls.V26_04
        raise ValidationError(f"Unknown protocol version: {s}")


def _parse_blame(blame_data: dict) -> Blame:
    original_line_range = None
    if "originalLineRange" in blame_data:
        rng = blame_data["originalLineRange"]
        original_line_range = LineRange(
            from_=rng["from"], to_=rng["to"], genRatio=0, genMethod="Manual"
        )
    return Blame(
        revisionId=blame_data["revisionId"],
        originalFilePath=blame_data["originalFilePath"],
        originalLine=blame_data.get("originalLine"),
        timestamp=blame_data.get("timestamp"),
        author=blame_data.get("author"),
        originalLineRange=original_line_range,
    )


def _parse_summary(summary_data: dict) -> Summary:
    return Summary(
        totalCodeLines=summary_data["totalCodeLines"],
        fullGeneratedCodeLines=summary_data["fullGeneratedCodeLines"],
        partialGeneratedCodeLines=summary_data["partialGeneratedCodeLines"],
        totalDocLines=summary_data["totalDocLines"],
        fullGeneratedDocLines=summary_data["fullGeneratedDocLines"],
        partialGeneratedDocLines=summary_data["partialGeneratedDocLines"],
    )


def _parse_v2603_code_line(entry: dict):
    if "lineLocation" in entry:
        return LineLocation(
            lineLocation=entry["lineLocation"],
            genRatio=entry["genRatio"],
            genMethod=entry["genMethod"],
        )
    if "lineRange" in entry:
        rng = entry["lineRange"]
        return LineRange(
            from_=rng["from"], to_=rng["to"],
            genRatio=entry["genRatio"], genMethod=entry["genMethod"],
        )
    raise ValidationError(f"v26.03 DETAIL entry must have lineLocation or lineRange: {entry}")


def _parse_v2604_code_line(entry: dict):
    change_type = entry["changeType"]
    if change_type == "add":
        add_entry = DetailAddEntry(
            changeType="add",
            genRatio=entry["genRatio"],
            genMethod=entry["genMethod"],
            blame=_parse_blame(entry["blame"]),
        )
        if "lineLocation" in entry:
            add_entry.lineLocation = entry["lineLocation"]
        if "lineRange" in entry:
            rng = entry["lineRange"]
            add_entry.lineRange = LineRange(
                from_=rng["from"], to_=rng["to"], genRatio=add_entry.genRatio, genMethod=add_entry.genMethod,
            )
        return add_entry
    if change_type == "delete":
        return DetailDeleteEntry(
            changeType="delete",
            blame=_parse_blame(entry["blame"]),
            lineLocation=entry.get("lineLocation"),
        )
    raise ValidationError(f"v26.04 DETAIL entry has unknown changeType: {change_type}")


def _parse_v2603_detail(detail_data: list) -> List[DetailFileV2603]:
    files = []
    for file_entry in detail_data:
        df = DetailFileV2603(fileName=file_entry["fileName"])
        if "codeLines" in file_entry:
            df.codeLines = [_parse_v2603_code_line(e) for e in file_entry["codeLines"]]
        if "docLines" in file_entry:
            df.docLines = [_parse_v2603_code_line(e) for e in file_entry["docLines"]]
        files.append(df)
    return files


def _parse_v2604_detail(detail_data: list) -> List[DetailFileV2604]:
    files = []
    for file_entry in detail_data:
        df = DetailFileV2604(fileName=file_entry["fileName"])
        if "codeLines" in file_entry:
            df.codeLines = [_parse_v2604_code_line(e) for e in file_entry["codeLines"]]
        if "docLines" in file_entry:
            df.docLines = [_parse_v2604_code_line(e) for e in file_entry["docLines"]]
        files.append(df)
    return files


def _parse_v2603_record(data: dict) -> GenCodeDescV2603:
    repo = Repository(
        vcsType=data["REPOSITORY"]["vcsType"],
        repoURL=data["REPOSITORY"]["repoURL"],
        repoBranch=data["REPOSITORY"]["repoBranch"],
        revisionId=data["REPOSITORY"]["revisionId"],
    )
    return GenCodeDescV2603(
        protocolName=data.get("protocolName", "generatedTextDesc"),
        protocolVersion="26.03",
        codeAgent=data.get("codeAgent", "unknown"),
        SUMMARY=_parse_summary(data["SUMMARY"]),
        DETAIL=_parse_v2603_detail(data.get("DETAIL", [])),
        REPOSITORY=repo,
    )


def _parse_v2604_record(data: dict) -> GenCodeDescV2604:
    repo = RepositoryV2604(
        vcsType=data["REPOSITORY"]["vcsType"],
        repoURL=data["REPOSITORY"]["repoURL"],
        repoBranch=data["REPOSITORY"]["repoBranch"],
        revisionId=data["REPOSITORY"]["revisionId"],
        revisionTimestamp=data["REPOSITORY"].get("revisionTimestamp", ""),
    )
    return GenCodeDescV2604(
        protocolName=data.get("protocolName", "generatedTextDesc"),
        protocolVersion="26.04",
        codeAgent=data.get("codeAgent", "unknown"),
        SUMMARY=_parse_summary(data["SUMMARY"]),
        DETAIL=_parse_v2604_detail(data.get("DETAIL", [])),
        REPOSITORY=repo,
    )


def _validate_repo_match(
    record: Union[GenCodeDescV2603, GenCodeDescV2604],
    expected_repo_url: Optional[str],
    expected_repo_branch: Optional[str],
    expected_revision_id: Optional[str],
) -> None:
    repo = record.REPOSITORY
    if expected_repo_url is not None and repo.repoURL != expected_repo_url:
        raise ValidationError(
            f"REPOSITORY.repoURL mismatch: expected '{expected_repo_url}', got '{repo.repoURL}'"
        )
    if expected_repo_branch is not None and repo.repoBranch != expected_repo_branch:
        raise ValidationError(
            f"REPOSITORY.repoBranch mismatch: expected '{expected_repo_branch}', got '{repo.repoBranch}'"
        )
    if expected_revision_id is not None and repo.revisionId != expected_revision_id:
        raise ValidationError(
            f"REPOSITORY.revisionId mismatch: expected '{expected_revision_id}', got '{repo.revisionId}'"
        )


def load_gen_code_desc(
    filepath: str,
    expected_repo_url: Optional[str] = None,
    expected_repo_branch: Optional[str] = None,
    expected_revision_id: Optional[str] = None,
) -> Union[GenCodeDescV2603, GenCodeDescV2604]:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    version_str = data.get("protocolVersion", "")
    version = ProtocolVersion.from_string(version_str)

    if version == ProtocolVersion.V26_03:
        record = _parse_v2603_record(data)
        from aggregateGenCodeDesc.models import validate_gen_code_desc_v2603
        validate_gen_code_desc_v2603(record)
    elif version == ProtocolVersion.V26_04:
        record = _parse_v2604_record(data)
        from aggregateGenCodeDesc.models import validate_gen_code_desc_v2604
        validate_gen_code_desc_v2604(record)
    else:
        raise ValidationError(f"Unsupported protocol version: {version_str}")

    _validate_repo_match(record, expected_repo_url, expected_repo_branch, expected_revision_id)
    return record


def load_gen_code_desc_dir(
    dirpath: str,
    expected_repo_url: Optional[str] = None,
    expected_repo_branch: Optional[str] = None,
) -> List[Union[GenCodeDescV2603, GenCodeDescV2604]]:
    path = Path(dirpath)
    if not path.is_dir():
        raise ValidationError(f"genCodeDescDir is not a directory: {dirpath}")

    json_files = sorted(path.glob("*.json"))
    if not json_files:
        return []

    first = load_gen_code_desc(
        str(json_files[0]),
        expected_repo_url=expected_repo_url,
        expected_repo_branch=expected_repo_branch,
    )
    first_version = ProtocolVersion.from_string(first.protocolVersion)

    records = [first]

    for jf in json_files[1:]:
        record = load_gen_code_desc(
            str(jf),
            expected_repo_url=expected_repo_url,
            expected_repo_branch=expected_repo_branch,
        )
        record_version = ProtocolVersion.from_string(record.protocolVersion)
        if record_version != first_version:
            raise ValidationError(
                f"Mixed protocol versions in genCodeDescDir: found {record_version.value} "
                f"after {first_version.value} in file {jf.name}"
            )
        records.append(record)

    return records
