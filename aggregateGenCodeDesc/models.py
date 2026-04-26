from dataclasses import dataclass, field
from typing import List, Optional, Union


class ValidationError(Exception):
    pass


@dataclass
class LineLocation:
    lineLocation: int
    genRatio: int
    genMethod: str


@dataclass
class LineRange:
    from_: int
    to_: int
    genRatio: int
    genMethod: str

    def __len__(self) -> int:
        return self.to_ - self.from_ + 1


@dataclass
class Summary:
    totalCodeLines: int
    fullGeneratedCodeLines: int
    partialGeneratedCodeLines: int
    totalDocLines: int
    fullGeneratedDocLines: int
    partialGeneratedDocLines: int

    @property
    def code_invariant_holds(self) -> bool:
        return self.totalCodeLines >= self.fullGeneratedCodeLines + self.partialGeneratedCodeLines

    @property
    def doc_invariant_holds(self) -> bool:
        return self.totalDocLines >= self.fullGeneratedDocLines + self.partialGeneratedDocLines


@dataclass
class Repository:
    vcsType: str
    repoURL: str
    repoBranch: str
    revisionId: str


@dataclass
class RepositoryV2604(Repository):
    revisionTimestamp: str = ""


CodeLineEntryV2603 = Union[LineLocation, LineRange]
DocLineEntryV2603 = Union[LineLocation, LineRange]


@dataclass
class DetailFileV2603:
    fileName: str
    codeLines: List[CodeLineEntryV2603] = field(default_factory=list)
    docLines: List[DocLineEntryV2603] = field(default_factory=list)


@dataclass
class GenCodeDescV2603:
    SUMMARY: Summary
    DETAIL: List[DetailFileV2603]
    REPOSITORY: Repository
    protocolName: str = "generatedTextDesc"
    protocolVersion: str = "26.03"
    codeAgent: str = "aggregateGenCodeDesc"


@dataclass
class Blame:
    revisionId: str
    originalFilePath: str
    originalLine: Optional[int] = None
    timestamp: Optional[str] = None
    author: Optional[str] = None
    originalLineRange: Optional[LineRange] = None


@dataclass
class BlameLineRange:
    revisionId: str
    originalFilePath: str
    originalLineRange: LineRange


@dataclass
class DetailAddEntry:
    changeType: str
    genRatio: int
    genMethod: str
    blame: Blame
    lineLocation: Optional[int] = None
    lineRange: Optional[LineRange] = None

    def __post_init__(self):
        if self.changeType != "add":
            raise ValidationError(f"DetailAddEntry changeType must be 'add', got '{self.changeType}'")


@dataclass
class DetailDeleteEntry:
    changeType: str
    blame: Blame
    lineLocation: Optional[int] = None

    def __post_init__(self):
        if self.changeType != "delete":
            raise ValidationError(f"DetailDeleteEntry changeType must be 'delete', got '{self.changeType}'")


DetailEntryV2604 = Union[DetailAddEntry, DetailDeleteEntry]


@dataclass
class DetailFileV2604:
    fileName: str
    codeLines: List[DetailEntryV2604] = field(default_factory=list)
    docLines: List[DetailEntryV2604] = field(default_factory=list)


@dataclass
class GenCodeDescV2604:
    SUMMARY: Summary
    DETAIL: List[DetailFileV2604]
    REPOSITORY: RepositoryV2604
    protocolName: str = "generatedTextDesc"
    protocolVersion: str = "26.04"
    codeAgent: str = "aggregateGenCodeDesc"


def _validate_gen_ratio(genRation: int, context: str = "") -> None:
    if not (0 <= genRation <= 100):
        msg = f"genRatio must be 0-100, got {genRation}"
        if context:
            msg = f"{msg} ({context})"
        raise ValidationError(msg)


def _validate_code_lines_v2603(lines: List[CodeLineEntryV2603], context: str = "") -> None:
    for entry in lines:
        if isinstance(entry, (LineLocation, LineRange)):
            _validate_gen_ratio(entry.genRatio, context)


def _validate_doc_lines_v2603(lines: List[DocLineEntryV2603], context: str = "") -> None:
    for entry in lines:
        if isinstance(entry, (LineLocation, LineRange)):
            _validate_gen_ratio(entry.genRatio, context)


def validate_gen_code_desc_v2603(record: GenCodeDescV2603) -> None:
    if not record.SUMMARY.code_invariant_holds:
        raise ValidationError(
            f"SUMMARY invariant violated: totalCodeLines ({record.SUMMARY.totalCodeLines}) "
            f"< fullGeneratedCodeLines ({record.SUMMARY.fullGeneratedCodeLines}) "
            f"+ partialGeneratedCodeLines ({record.SUMMARY.partialGeneratedCodeLines})"
        )
    if not record.SUMMARY.doc_invariant_holds:
        raise ValidationError(
            f"SUMMARY invariant violated: totalDocLines ({record.SUMMARY.totalDocLines}) "
            f"< fullGeneratedDocLines ({record.SUMMARY.fullGeneratedDocLines}) "
            f"+ partialGeneratedDocLines ({record.SUMMARY.partialGeneratedDocLines})"
        )
    for df in record.DETAIL:
        _validate_code_lines_v2603(df.codeLines, f"file={df.fileName}")
        _validate_doc_lines_v2603(df.docLines, f"file={df.fileName}")


def _validate_code_lines_v2604(lines: List[DetailEntryV2604], context: str = "") -> None:
    for entry in lines:
        if isinstance(entry, DetailAddEntry):
            _validate_gen_ratio(entry.genRatio, context)


def _validate_doc_lines_v2604(lines: List[DetailEntryV2604], context: str = "") -> None:
    for entry in lines:
        if isinstance(entry, DetailAddEntry):
            _validate_gen_ratio(entry.genRatio, context)


def validate_gen_code_desc_v2604(record: GenCodeDescV2604) -> None:
    if not record.SUMMARY.code_invariant_holds:
        raise ValidationError(
            f"SUMMARY invariant violated: totalCodeLines ({record.SUMMARY.totalCodeLines}) "
            f"< fullGeneratedCodeLines ({record.SUMMARY.fullGeneratedCodeLines}) "
            f"+ partialGeneratedCodeLines ({record.SUMMARY.partialGeneratedCodeLines})"
        )
    if not record.SUMMARY.doc_invariant_holds:
        raise ValidationError(
            f"SUMMARY invariant violated: totalDocLines ({record.SUMMARY.totalDocLines}) "
            f"< fullGeneratedDocLines ({record.SUMMARY.fullGeneratedDocLines}) "
            f"+ partialGeneratedDocLines ({record.SUMMARY.partialGeneratedDocLines})"
        )
    for df in record.DETAIL:
        _validate_code_lines_v2604(df.codeLines, f"file={df.fileName}")
        _validate_doc_lines_v2604(df.docLines, f"file={df.fileName}")
