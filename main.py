import chromadb
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

from agent.answer import generate_answer
from agent.confidence import score_confidence
from ingest.store_ingest import ingest_store, load_store_from_json
from intelligence.missing_info import (
    cluster_missing_questions,
    get_missing_questions,
    log_missing,
)
from retrieval.classifier import classify_question
from retrieval.retriever import retrieve

app = FastAPI(title="Store Knowledge Agent")

# Shared in-memory ChromaDB client and store registry
_chroma_client = chromadb.Client()
_loaded_stores: dict = {}

app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Request models ────────────────────────────────────────────────────────────

class LoadStoreRequest(BaseModel):
    store_json_path: str = "sample_data/sample_store.json"


class ChatRequest(BaseModel):
    store_id: str
    question: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/load-store")
async def load_store(req: LoadStoreRequest):
    try:
        store = load_store_from_json(req.store_json_path)
        result = ingest_store(store, _chroma_client)
        _loaded_stores[store.store_id] = store
        return {
            "store_id": store.store_id,
            "store_name": store.store_name,
            "products_ingested": result["products_ingested"],
            "policies_ingested": result["policies_ingested"],
            "faqs_ingested": result["faqs_ingested"],
        }
    except FileNotFoundError as e:
        return JSONResponse(
            status_code=404,
            content={"error": "Store file not found", "detail": str(e)},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to load store", "detail": type(e).__name__},
        )


@app.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        if req.store_id not in _loaded_stores:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Store not loaded. Call /api/load-store first.",
                    "detail": f"Unknown store_id: {req.store_id}",
                },
            )

        question_type = classify_question(req.question)
        sources = retrieve(req.question, req.store_id, question_type, _chroma_client)

        # Direct FAQ return — skip LLM generation
        faq_exact = next(
            (s for s in sources if s.chunk_type == "faq_exact_match"), None
        )
        if faq_exact:
            answer = faq_exact.text
        else:
            try:
                answer = generate_answer(req.question, sources)
            except Exception:
                # LLM unavailable — surface retrieved text directly
                if sources:
                    answer = sources[0].text
                else:
                    answer = "I don't have information about that in our store knowledge base."

        confidence = score_confidence(req.question, answer, sources)

        if confidence.flagged_missing:
            log_missing(req.question, confidence.score, question_type)

        return {
            "question": req.question,
            "question_type": question_type,
            "answer": answer,
            "sources": [
                {
                    "chunk_id": s.chunk_id,
                    "chunk_type": s.chunk_type,
                    "text": s.text,
                    "relevance_score": s.relevance_score,
                }
                for s in sources
            ],
            "confidence": {
                "score": confidence.score,
                "retrieval_hit": confidence.retrieval_hit,
                "hedge_detected": confidence.hedge_detected,
                "flagged_missing": confidence.flagged_missing,
                "reason": confidence.reason,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": type(e).__name__},
        )


@app.get("/api/missing-info")
def missing_info():
    questions = get_missing_questions()
    return {
        "total": len(questions),
        "questions": [
            {
                "question": q.question,
                "asked_at": q.asked_at,
                "confidence_score": q.confidence_score,
                "question_type": q.question_type,
            }
            for q in questions
        ],
    }


@app.post("/api/cluster-gaps")
async def cluster_gaps():
    try:
        report = cluster_missing_questions()
        return {
            "total_unanswered": report.total_unanswered,
            "generated_at": report.generated_at,
            "clusters": [
                {
                    "topic": c.topic,
                    "questions": c.questions,
                    "count": c.count,
                    "gap_score": c.gap_score,
                    "recommendation": c.recommendation,
                }
                for c in report.clusters
            ],
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Clustering failed", "detail": type(e).__name__},
        )
