import re

from llm.client import classify as llm_classify

_PRODUCT_RE = re.compile(
    r"\b(price|cost|material|size|color|colour|stock|available|weight|fit|fits|"
    r"runs true|true to size|sizing|sized|run small|run large|run big|"
    r"jacket|backpack|bottle|supplement|protein|buff|poles|fabric|made of|"
    r"what is the|how much|ingredients|variants|colors|colours|vegan|"
    r"waterproof|rating|capacity|insulated|down fill|materials|specs|specification)\b",
    re.IGNORECASE,
)

_POLICY_RE = re.compile(
    r"\b(return|refund|exchange|ship|shipping|deliver|delivery|warranty|guarantee|"
    r"policy|policies|days|international|expedited|free shipping|tracking|order status)\b",
    re.IGNORECASE,
)

_FAQ_RE = re.compile(
    r"\b(how do i|can i|do you|is it|are you|do i|will you|does it|is there|"
    r"how to|what happens|when will)\b",
    re.IGNORECASE,
)


def classify_question(question: str) -> str:
    product_match = bool(_PRODUCT_RE.search(question))
    policy_match = bool(_POLICY_RE.search(question))
    faq_match = bool(_FAQ_RE.search(question))

    if product_match and policy_match:
        return "mixed"
    if product_match:
        return "product_query"
    if policy_match:
        return "policy_query"
    if faq_match:
        return "faq_query"

    # Fall back to LLM classifier
    try:
        result = llm_classify(question)
        if result in ("product_query", "policy_query", "faq_query", "mixed"):
            return result
    except Exception:
        pass

    # Final heuristic fallback: default based on question structure
    q_lower = question.lower()
    if any(w in q_lower for w in ("safe", "safe for", "okay", "ok to", "can i use", "suitable for")):
        return "product_query"
    return "faq_query"
