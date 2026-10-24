
import re
from dataclasses import dataclass


@dataclass
class EvidenceResult:
    valid: bool
    answer: str = ""
    reason: str = ""


def normalize(text: str) -> str:
    text = text.casefold()
    text = re.sub(r"[^\w€£$%–-]+", " ", text)
    return " ".join(text.split())


def render_verified_answer(
    claims: list,
    sources: dict,
) -> EvidenceResult:
    if not claims:
        return EvidenceResult(False, reason="no_claims")

    rendered = []

    for claim in claims:
        statement = claim["text"].strip()
        source_ids = claim["source_ids"]

        if not statement or not source_ids:
            return EvidenceResult(False, reason="invalid_claim")

        for source_id in source_ids:
            source = sources.get(source_id)

            if source is None:
                return EvidenceResult(
                    False,
                    reason="unknown_source",
                )

            # Strict extractive validation.
            if normalize(statement) not in normalize(source["text"]):
                return EvidenceResult(
                    False,
                    reason="claim_not_found_in_evidence",
                )

        citation = " ".join(
            f"[{source_id}]" for source_id in source_ids
        )

        rendered.append(
            f"{statement.rstrip('. ')}. {citation}"
        )

    return EvidenceResult(
        valid=True,
        answer=" ".join(rendered),
    )