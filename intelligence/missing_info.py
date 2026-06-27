from datetime import datetime, timezone
from typing import List

from llm.client import cluster_questions
from models.response import GapCluster, MissingInfoReport, MissingQuestion

_missing_questions: List[MissingQuestion] = []


def log_missing(question: str, confidence: float, question_type: str) -> None:
    _missing_questions.append(
        MissingQuestion(
            question=question,
            asked_at=datetime.now(timezone.utc).isoformat(),
            confidence_score=round(confidence, 4),
            question_type=question_type,
        )
    )


def get_missing_questions() -> List[MissingQuestion]:
    return sorted(_missing_questions, key=lambda q: q.asked_at, reverse=True)


def cluster_missing_questions() -> MissingInfoReport:
    generated_at = datetime.now(timezone.utc).isoformat()

    if not _missing_questions:
        return MissingInfoReport(
            total_unanswered=0,
            clusters=[],
            generated_at=generated_at,
        )

    question_texts = [q.question for q in _missing_questions]
    question_confidence = {q.question: q.confidence_score for q in _missing_questions}

    raw_clusters = cluster_questions(question_texts)

    clusters: List[GapCluster] = []
    for raw in raw_clusters:
        topic = raw.get("topic", "Uncategorized")
        qs = raw.get("questions", [])
        recommendation = raw.get("recommendation", "")
        count = len(qs)

        confidences = [question_confidence.get(q, 0.5) for q in qs]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        gap_score = round(count * (1 - avg_confidence), 4)

        clusters.append(
            GapCluster(
                topic=topic,
                questions=qs,
                count=count,
                gap_score=gap_score,
                recommendation=recommendation,
            )
        )

    clusters.sort(key=lambda c: c.gap_score, reverse=True)

    return MissingInfoReport(
        total_unanswered=len(_missing_questions),
        clusters=clusters,
        generated_at=generated_at,
    )
