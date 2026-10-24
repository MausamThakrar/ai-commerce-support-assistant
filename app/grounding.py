
import re
from dataclasses import dataclass


@dataclass
class GroundingResult:
    valid: bool
    reason: str = ""


# Patterns indicating that the assistant is making
# a definite commitment on behalf of the store.
COMMITMENT_PATTERNS = [
    r"\byou (?:can|will) (?:get|receive) (?:a |an )?(?:full )?refund\b",
    r"\byou are (?:entitled to|guaranteed) (?:a |an )?(?:full )?refund\b",
    r"\bwe (?:will|guarantee to) (?:refund|replace|cancel)\b",
    r"\byou (?:will|definitely) (?:receive|get) (?:a |an )?replacement\b",
]

UNSUPPORTED_PATTERNS = [
    r"\bknowledge context does not\b",
    r"\bprovided context does not\b",
    r"\bI (?:do not|don't) have enough information\b",
    r"\bI (?:cannot|can't) (?:confirm|verify|determine)\b",
]


class GroundingValidator:
    def validate(self, answer: str, sources: list) -> GroundingResult:
        if not answer.strip():
            return GroundingResult(False, "empty_answer")

        if any(
            re.search(pattern, answer, re.IGNORECASE)
            for pattern in UNSUPPORTED_PATTERNS
        ):
            return GroundingResult(False, "insufficient_evidence")

        if any(
            re.search(pattern, answer, re.IGNORECASE)
            for pattern in COMMITMENT_PATTERNS
        ):
            return GroundingResult(False, "unsupported_commitment")

        if not sources:
            return GroundingResult(False, "missing_sources")

        return GroundingResult(True)