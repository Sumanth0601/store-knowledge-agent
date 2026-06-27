from typing import List

from llm.client import complete
from models.response import SourceChunk

_SYSTEM_PROMPT = (
    "You are a helpful store assistant. Answer the shopper's question using only the "
    "information in the provided store knowledge. Be specific and direct. "
    "If the information is not available, say clearly that you don't have that "
    "information rather than guessing."
)


def generate_answer(question: str, sources: List[SourceChunk]) -> str:
    if not sources:
        return "I don't have information about that in our store knowledge base."

    context_parts = []
    for i, source in enumerate(sources, 1):
        context_parts.append(f"[{source.chunk_type.upper()} {i}]\n{source.text}")

    context = "\n\n".join(context_parts)
    user_message = f"Store knowledge:\n{context}\n\nShopper question: {question}"

    return complete(_SYSTEM_PROMPT, user_message)
