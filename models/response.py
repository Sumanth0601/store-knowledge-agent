from dataclasses import dataclass
from typing import List


@dataclass
class SourceChunk:
    chunk_id: str
    chunk_type: str  # "product", "policy", "faq", "faq_exact_match"
    text: str
    relevance_score: float


@dataclass
class ConfidenceScore:
    score: float           # 0.0 to 1.0
    retrieval_hit: bool    # Was a relevant chunk retrieved?
    hedge_detected: bool   # Did the model hedge its answer?
    flagged_missing: bool  # Is this logged as unanswered?
    reason: str


@dataclass
class ChatResponse:
    question: str
    question_type: str
    answer: str
    sources: List[SourceChunk]
    confidence: ConfidenceScore


@dataclass
class MissingQuestion:
    question: str
    asked_at: str
    confidence_score: float
    question_type: str


@dataclass
class GapCluster:
    topic: str
    questions: List[str]
    count: int
    gap_score: float       # count * (1 - avg_confidence)
    recommendation: str


@dataclass
class MissingInfoReport:
    total_unanswered: int
    clusters: List[GapCluster]
    generated_at: str
