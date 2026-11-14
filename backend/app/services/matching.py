"""Semantic-ish lost & found matching.

Uses TF-IDF vectors + cosine similarity, implemented in pure Python so it runs
offline with no model download. The interface is deliberately small: swap
`rank()` for sentence-transformers embeddings later without touching the API.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Match, Report

STOPWORDS = {
    "the", "and", "for", "with", "from", "near", "that", "this", "was", "were",
    "has", "have", "had", "its", "his", "her", "their", "our", "your", "you",
    "but", "not", "are", "been", "being", "into", "onto", "over", "under",
    "about", "after", "before", "between", "during", "while", "when", "where",
    "who", "whom", "which", "what", "why", "how", "all", "any", "some", "one",
    "two", "very", "just", "also", "then", "than", "them", "they", "there",
    "here", "can", "could", "would", "should", "will", "shall", "may", "might",
    "must", "did", "does", "doing", "done", "got", "get", "gets", "lost",
    "found", "missing", "item", "items", "please", "someone", "anyone",
}

DEFAULT_THRESHOLD = 0.15
DEFAULT_LIMIT = 5


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    out: list[str] = []
    for word in words:
        if len(word) < 3 or word in STOPWORDS:
            continue
        if word.endswith("s") and len(word) > 4:
            word = word[:-1]
        out.append(word)
    return out


def _document(report: Report) -> str:
    # Repeated fields act as weights: title x3, category x2.
    return " ".join(
        [
            report.title,
            report.title,
            report.title,
            report.category,
            report.category,
            report.description,
            report.location,
            report.location,
        ]
    )


def _tfidf_vectors(docs: list[str]) -> list[dict[str, float]]:
    tokenized = [_tokens(doc) for doc in docs]
    doc_freq: Counter[str] = Counter()
    for tokens in tokenized:
        doc_freq.update(set(tokens))

    total_docs = len(tokenized)
    vectors: list[dict[str, float]] = []
    for tokens in tokenized:
        counts = Counter(tokens)
        length = sum(counts.values()) or 1
        vector: dict[str, float] = {}
        for term, count in counts.items():
            idf = math.log((1 + total_docs) / (1 + doc_freq[term])) + 1
            vector[term] = (count / length) * idf
        norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
        vectors.append({term: value / norm for term, value in vector.items()})
    return vectors


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    return sum(value * b.get(term, 0.0) for term, value in a.items())


def rank(query: Report, candidates: list[Report]) -> list[tuple[Report, float, list[str]]]:
    """Return (candidate, score 0..1, reasons) sorted by score."""
    if not candidates:
        return []

    vectors = _tfidf_vectors([_document(query)] + [_document(c) for c in candidates])
    query_vector = vectors[0]
    query_keywords = set(_tokens(f"{query.title} {query.description}"))
    query_location = set(_tokens(query.location))

    results: list[tuple[Report, float, list[str]]] = []
    for candidate, vector in zip(candidates, vectors[1:]):
        score = _cosine(query_vector, vector)
        reasons: list[str] = []

        shared = sorted(
            query_keywords & set(_tokens(f"{candidate.title} {candidate.description}"))
        )
        if shared:
            reasons.append("shared keywords: " + ", ".join(shared[:5]))

        if candidate.category.lower() == query.category.lower():
            score += 0.06
            reasons.append(f"same category ({candidate.category})")

        candidate_location = set(_tokens(candidate.location))
        if query_location and candidate_location:
            if query_location == candidate_location:
                score += 0.05
                reasons.append("same location")
            elif query_location & candidate_location:
                score += 0.02
                reasons.append("nearby location")

        if not reasons:
            reasons.append("similar description")

        results.append((candidate, max(0.0, min(0.99, score)), reasons))

    return sorted(results, key=lambda row: row[1], reverse=True)


def ensure_matches(
    db: Session,
    report: Report,
    *,
    limit: int = DEFAULT_LIMIT,
    threshold: float = DEFAULT_THRESHOLD,
) -> list[Match]:
    """Compare a report against opposite-type reports and store new matches."""
    opposite = "found" if report.type == "lost" else "lost"
    candidates = list(
        db.scalars(
            select(Report).where(
                Report.type == opposite,
                Report.status.in_(["open", "matched"]),
                Report.id != report.id,
            )
        ).all()
    )

    created: list[Match] = []
    for candidate, score, reasons in rank(report, candidates)[:limit]:
        if score < threshold:
            continue
        lost_id, found_id = (
            (report.id, candidate.id)
            if report.type == "lost"
            else (candidate.id, report.id)
        )
        exists = db.scalar(
            select(Match).where(
                Match.lost_report_id == lost_id,
                Match.found_report_id == found_id,
            )
        )
        if exists:
            continue
        match = Match(
            lost_report_id=lost_id,
            found_report_id=found_id,
            score=round(score, 4),
            reasons="; ".join(reasons),
        )
        db.add(match)
        created.append(match)

    db.flush()
    return created
