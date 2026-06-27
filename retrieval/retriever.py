from typing import List, Optional

from ingest.store_ingest import get_embedder
from models.response import SourceChunk

FAQ_EXACT_MATCH_THRESHOLD = 0.85


def _query_collection(collection, query_embedding: list, top_k: int, chunk_type: str) -> List[SourceChunk]:
    count = collection.count()
    if count == 0:
        return []
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, count),
        include=["documents", "distances", "metadatas"],
    )
    chunks = []
    if not results["ids"] or not results["ids"][0]:
        return chunks
    for i, doc_id in enumerate(results["ids"][0]):
        distance = results["distances"][0][i]
        similarity = max(0.0, 1.0 - distance)  # cosine distance → similarity
        text = results["documents"][0][i]
        chunks.append(
            SourceChunk(
                chunk_id=doc_id,
                chunk_type=chunk_type,
                text=text,
                relevance_score=round(similarity, 4),
            )
        )
    return chunks


def _enrich_faq_chunks(chunks: List[SourceChunk], faq_col) -> List[SourceChunk]:
    """Replace question-only text with Q+A format for faq chunks."""
    enriched = []
    for chunk in chunks:
        if chunk.chunk_type == "faq":
            try:
                result = faq_col.get(ids=[chunk.chunk_id], include=["metadatas"])
                if result["metadatas"]:
                    meta = result["metadatas"][0]
                    q = meta.get("question", "")
                    a = meta.get("answer", "")
                    chunk = SourceChunk(
                        chunk_id=chunk.chunk_id,
                        chunk_type="faq",
                        text=f"Q: {q}\nA: {a}",
                        relevance_score=chunk.relevance_score,
                    )
            except Exception:
                pass
        enriched.append(chunk)
    return enriched


def retrieve(
    question: str,
    store_id: str,
    question_type: str,
    chroma_client,
    top_k: int = 4,
) -> List[SourceChunk]:
    embedder = get_embedder()
    query_embedding = embedder.encode([question]).tolist()[0]

    def get_col(name):
        try:
            return chroma_client.get_collection(name)
        except Exception:
            return None

    products_col = get_col(f"products_{store_id}")
    policies_col = get_col(f"policies_{store_id}")
    faq_col = get_col(f"faq_{store_id}")

    # Always check for FAQ exact match first
    if faq_col and faq_col.count() > 0:
        faq_results = faq_col.query(
            query_embeddings=[query_embedding],
            n_results=1,
            include=["documents", "distances", "metadatas"],
        )
        if faq_results["ids"] and faq_results["ids"][0]:
            distance = faq_results["distances"][0][0]
            similarity = max(0.0, 1.0 - distance)
            if similarity >= FAQ_EXACT_MATCH_THRESHOLD:
                meta = faq_results["metadatas"][0][0]
                answer_text = meta.get("answer", faq_results["documents"][0][0])
                return [
                    SourceChunk(
                        chunk_id=faq_results["ids"][0][0],
                        chunk_type="faq_exact_match",
                        text=answer_text,
                        relevance_score=round(similarity, 4),
                    )
                ]

    # Route by question type
    chunks: List[SourceChunk] = []

    if question_type == "product_query":
        if products_col:
            chunks += _query_collection(products_col, query_embedding, 4, "product")

    elif question_type == "policy_query":
        if policies_col:
            chunks += _query_collection(policies_col, query_embedding, 3, "policy")
        if faq_col:
            chunks += _query_collection(faq_col, query_embedding, 1, "faq")

    elif question_type == "faq_query":
        if faq_col:
            chunks += _query_collection(faq_col, query_embedding, 2, "faq")
        if products_col:
            chunks += _query_collection(products_col, query_embedding, 2, "product")

    else:  # mixed
        if products_col:
            chunks += _query_collection(products_col, query_embedding, 2, "product")
        if policies_col:
            chunks += _query_collection(policies_col, query_embedding, 2, "policy")
        if faq_col:
            chunks += _query_collection(faq_col, query_embedding, 2, "faq")
        # Deduplicate and take top-4
        seen: set = set()
        unique: List[SourceChunk] = []
        for c in chunks:
            if c.chunk_id not in seen:
                seen.add(c.chunk_id)
                unique.append(c)
        chunks = sorted(unique, key=lambda x: x.relevance_score, reverse=True)[:top_k]

    # Enrich FAQ chunks with Q+A text
    if faq_col:
        chunks = _enrich_faq_chunks(chunks, faq_col)

    return chunks
