from enum import Enum
from typing import List

from aggregateGenCodeDesc.models import GenCodeDescV2603, GenCodeDescV2604


class OnMissingPolicy(str, Enum):
    ZERO = "zero"
    ABORT = "abort"
    SKIP = "skip"


class OnDuplicatePolicy(str, Enum):
    REJECT = "reject"
    LAST_WINS = "last-wins"


class OnClockSkewPolicy(str, Enum):
    ABORT = "abort"
    IGNORE = "ignore"


def check_clock_skew(records: List[GenCodeDescV2604]) -> bool:
    if len(records) < 2:
        return False
    for i in range(len(records) - 1):
        if records[i].REPOSITORY.revisionTimestamp > records[i + 1].REPOSITORY.revisionTimestamp:
            return True
    return False


def check_duplicate_revisions(records: List) -> List[str]:
    seen = {}
    duplicates = []
    for r in records:
        rev_id = r.REPOSITORY.revisionId
        if rev_id in seen:
            duplicates.append(rev_id)
        seen[rev_id] = r
    return duplicates
