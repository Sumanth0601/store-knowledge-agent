import json
import os
from typing import List

from openai import OpenAI


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable not set")
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def complete(
    system_prompt: str,
    user_message: str,
    model: str = "google/gemma-3-27b-it",
) -> str:
    client = _get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0,
    )
    return response.choices[0].message.content.strip()


def classify(question: str) -> str:
    client = _get_client()
    response = client.chat.completions.create(
        model="meta-llama/llama-3.1-8b-instruct",
        messages=[
            {
                "role": "system",
                "content": (
                    "Classify the following shopper question into exactly one category: "
                    "product_query, policy_query, faq_query, or mixed. "
                    "Respond with only the category name, nothing else."
                ),
            },
            {"role": "user", "content": question},
        ],
        temperature=0,
    )
    return response.choices[0].message.content.strip().lower()


def cluster_questions(questions: List[str]) -> List[dict]:
    client = _get_client()
    questions_text = "\n".join(f"- {q}" for q in questions)
    try:
        response = client.chat.completions.create(
            model="google/gemma-3-12b-it",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Group the following customer questions into thematic clusters. "
                        "For each cluster, provide a short topic name, the list of questions, "
                        "and a one-sentence recommendation for what store content would answer them. "
                        'Respond with valid JSON only: [{"topic": ..., "questions": [...], "recommendation": ...}]'
                    ),
                },
                {"role": "user", "content": questions_text},
            ],
            temperature=0,
        )
        content = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if "```" in content:
            parts = content.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                try:
                    return json.loads(part)
                except json.JSONDecodeError:
                    continue
        return json.loads(content)
    except Exception:
        return [
            {
                "topic": "Uncategorized",
                "questions": questions,
                "recommendation": (
                    "Review these unanswered questions and add relevant FAQ entries."
                ),
            }
        ]
