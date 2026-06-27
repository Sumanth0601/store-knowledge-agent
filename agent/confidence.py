from typing import List

from models.response import ConfidenceScore, SourceChunk

_HEDGE_PHRASES = [
    "i don't have information",
    "i do not have information",
    "not sure",
    "i cannot confirm",
    "no information available",
    "i'm unable to",
    "i am unable to",
    "i don't know",
    "i do not know",
    "i cannot find",
    "not available in",
    "unable to find",
    "no details available",
]

_RETRIEVAL_HIT_THRESHOLD = 0.45  # all-MiniLM-L6-v2 cosine similarities rarely exceed 0.7


def score_confidence(
    question: str,
    answer: str,
    sources: List[SourceChunk],
) -> ConfidenceScore:
    retrieval_hit = any(s.relevance_score > _RETRIEVAL_HIT_THRESHOLD for s in sources)

    answer_lower = answer.lower()
    hedge_detected = any(phrase in answer_lower for phrase in _HEDGE_PHRASES)

    # Base score: average of top-2 sources by relevance
    sorted_sources = sorted(sources, key=lambda s: s.relevance_score, reverse=True)
    top_two = sorted_sources[:2]
    base_score = (
        sum(s.relevance_score for s in top_two) / len(top_two) if top_two else 0.0
    )

    score = base_score
    if hedge_detected:
        score = min(score, 0.4)
    if not retrieval_hit:
        score = min(score, 0.35)

    score = round(score, 4)
    flagged_missing = score < 0.5

    # Human-readable reason
    if not sources:
        reason = "No relevant chunks retrieved"
    elif not retrieval_hit and hedge_detected:
        reason = "Answer hedged — model indicated missing information"
    elif not retrieval_hit:
        reason = "Low retrieval similarity — no close match found"
    elif hedge_detected:
        reason = "Answer hedged — model indicated missing information"
    elif score >= 0.8:
        reason = "Strong FAQ match"
    elif score >= 0.6:
        reason = "Good retrieval match"
    else:
        reason = "Partial match — answer may be incomplete"

    return ConfidenceScore(
        score=score,
        retrieval_hit=retrieval_hit,
        hedge_detected=hedge_detected,
        flagged_missing=flagged_missing,
        reason=reason,
    )
