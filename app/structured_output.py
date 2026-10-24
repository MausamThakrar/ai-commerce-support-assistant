
import json
from dataclasses import dataclass


ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["answered", "insufficient_evidence"],
        },
        "answer": {"type": "string"},
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "source_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["text", "source_ids"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["status", "answer", "claims"],
    "additionalProperties": False,
}


@dataclass
class StructuredAnswer:
    status: str
    answer: str
    claims: list


def parse_structured_answer(
    raw_content: str,
    allowed_source_ids: set,
) -> StructuredAnswer:
    try:
        data = json.loads(raw_content)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("Invalid model JSON") from exc

    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object")

    status = data.get("status")
    answer = data.get("answer")
    claims = data.get("claims")

    if status not in ("answered", "insufficient_evidence"):
        raise ValueError("Invalid answer status")

    if not isinstance(answer, str):
        raise ValueError("Invalid answer field")

    if not answer.strip():
        raise ValueError("Empty answer")

    if not isinstance(claims, list):
        raise ValueError("Invalid claims field")

    if status == "answered" and not claims:
        raise ValueError("No supported claims")

    if status == "insufficient_evidence" and claims:
        raise ValueError(
            "Unsupported answer must not contain claims"
        )

    for claim in claims:
        if not isinstance(claim, dict):
            raise ValueError("Invalid claim object")

        text = claim.get("text")
        source_ids = claim.get("source_ids")

        if not isinstance(text, str) or not text.strip():
            raise ValueError("Invalid claim text")

        if not isinstance(source_ids, list):
            raise ValueError("Invalid claim source IDs")

        if not source_ids:
            raise ValueError("Claim has no evidence")

        if not all(
            isinstance(source_id, str)
            for source_id in source_ids
        ):
            raise ValueError("Invalid source ID type")

        if not set(source_ids).issubset(allowed_source_ids):
            raise ValueError("Claim references unknown source")

    return StructuredAnswer(
        status=status,
        answer=answer.strip(),
        claims=claims,
    )