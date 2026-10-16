"""
Deterministic detection of documented changes in retrieved evidence.

Finds sentences that explicitly record a change to a value
("... was adjusted to ...", "... was moved to ...", "تم تعديل ... إلى")
and keeps the ones relevant to the question. They are passed to the LLM
quoted verbatim with their source file and page, so it does not have to
discover and classify revisions on its own.

Generic by design: only change-verb patterns, no business facts.
"""

import re

# ponytail: provisional threshold, calibrated on a small question set
# (see tests/test_evidence_notes.py); revisit when the corpus grows.
RELEVANCE_THRESHOLD = 0.40

_CHANGE_VERBS = (
    "revised|adjusted|amended|updated|changed|moved|postponed|"
    "rescheduled|delayed|increased|decreased|reduced|raised|lowered|"
    "replaced|superseded|extended|shortened"
)

CHANGE_PATTERN = re.compile(
    # "was adjusted to", "has been moved from", "were later revised to"
    rf"\b(?:was|were|has been|have been|had been)\s+(?:\w+\s+)?"
    rf"(?:{_CHANGE_VERBS})\s+(?:to|from)\b"
    # "تم تعديل ... إلى", "جرى تأجيل ... إلى"
    r"|(?:تم|جرى)\s+(?:تعديل|تأجيل|نقل|تغيير|تحديث|رفع|خفض|تمديد)\S*"
    r"\s+[^.!?؟]{0,80}?إلى",
    re.IGNORECASE,
)

_TASHKEEL = re.compile(r"[ً-ْ]")
_SENTENCE_END = re.compile(r"(?<=[.!?؟])\s+")


def split_sentences(text: str) -> list[str]:
    """Split page text into sentences (whitespace normalized, wording unchanged)."""
    flat = re.sub(r"\s+", " ", text).strip()
    return [s for s in _SENTENCE_END.split(flat) if s]


def detect_changes(chunks: list) -> list[dict]:
    """Return every sentence that explicitly records a change, with provenance."""
    found = []
    for chunk in chunks:
        for sentence in split_sentences(chunk["text"]):
            if CHANGE_PATTERN.search(_TASHKEEL.sub("", sentence)):
                found.append({
                    "source": chunk["source"],
                    "page": chunk["page"],
                    "text": sentence,
                })
    return found


def find_documented_changes(chunks: list, question: str, model) -> list[dict]:
    """
    Documented-change sentences from `chunks` that are relevant to `question`,
    scored with the already-loaded embedding model.
    """
    changes = detect_changes(chunks)
    if not changes:
        return []

    question_vec = model.encode(
        [question], normalize_embeddings=True, convert_to_numpy=True
    )[0]
    sentence_vecs = model.encode(
        [c["text"] for c in changes], normalize_embeddings=True, convert_to_numpy=True
    )
    scores = sentence_vecs @ question_vec

    return [
        {**change, "score": float(score)}
        for change, score in zip(changes, scores)
        if score >= RELEVANCE_THRESHOLD
    ]


def format_changes(changes: list) -> str:
    """Context block quoting each documented change verbatim with its citation."""
    lines = [
        "DOCUMENTED CHANGES (sentences found automatically in the excerpts "
        "above, quoted verbatim):"
    ]
    for c in changes:
        lines.append(f'- [SOURCE: {c["source"]} | PAGE: {c["page"]}] "{c["text"]}"')
    return "\n".join(lines)
