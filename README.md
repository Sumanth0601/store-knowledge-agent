# Store Knowledge Agent

An engineering prototype demonstrating two things: (1) a structured knowledge-retrieval agent that answers shopper questions using a store's own product, policy, and FAQ data — with a typed confidence signal on every response, and (2) a merchant-facing dashboard that surfaces the questions the agent *couldn't* answer, clusters them into themes, and recommends what content to add.

The demo is intentionally scoped. It shows that structuring retrieval by knowledge type beats naive flat-text RAG, and that every unanswered question is a structured merchant insight — not just a silent bounce.

---

## Screenshots

**Two-panel UI — shopper chat (left) + merchant gap dashboard (right)**

The left panel shows responses with confidence badges (yellow = partial match, red = gap). The right panel surfaces every low-confidence question in real time with timestamps and confidence scores.

![Overview](static/screenshots/overview.png)

**What the confidence badge signals:**
- `61% confident` (yellow) — "Do you ship to Canada?" retrieved the shipping policy, which explicitly says no Canada shipping. Good match, direct answer.
- `35% confident` (red) + `⚠ logged as gap` — "Is the protein powder safe during pregnancy?" found no relevant content. Flagged immediately in the right panel.
- The Missing Intelligence badge (red **3**) counts live as gaps accumulate. Click **Cluster Gaps** to group them into themes via LLM and get content recommendations.

---

## How to run

```bash
git clone https://github.com/Sumanth0601/store-knowledge-agent
cd store-knowledge-agent

pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your OpenRouter API key (free at https://openrouter.ai/keys)

uvicorn main:app --reload
# Open http://localhost:8000
# Click "Load Store", then start asking questions
```

---

## Demo script

Run these six questions in order. Watch the confidence badge and the right panel.

| # | Question | What to look for |
|---|----------|-----------------|
| 1 | *Does the Alpine jacket run true to size?* | FAQ exact match (≥0.85 cosine similarity) — high confidence, no LLM call made |
| 2 | *What is your return policy?* | Routes to `policies` collection — high confidence, policy text retrieved |
| 3 | *Do you ship to Canada?* | Policy retrieved mentions EU but not Canada — low confidence, appears immediately in right panel |
| 4 | *Is the protein powder safe during pregnancy?* | No relevant content exists — confidence <0.4, flagged in right panel |
| 5 | *Can I return a jacket I bought 6 weeks ago?* | Policy retrieved but model hedges (exceeds 30-day window) — medium-low confidence |
| 6 | Click **Cluster Gaps** → two clusters surface with gap scores and content recommendations |

The right panel populates in real time — every low-confidence response is logged immediately without any manual step.

---

## Architecture decisions

**Separate ChromaDB collections per knowledge type**
A single flat embedding space returns the wrong content predictably: a return policy question retrieves product descriptions that mention "returns accepted" in passing. By routing `policy_query` → `policies_*` collection and `product_query` → `products_*` collection, retrieval precision improves without any reranking overhead.

**Rule-based confidence scoring (no LLM judge)**
Confidence is computed deterministically from two signals: retrieval similarity (did any chunk score above 0.60?) and hedge detection (does the answer contain "I don't have information", "I cannot confirm", etc.). This is faster, cheaper, and deterministic at scale compared to asking an LLM to self-evaluate. The confidence badge difference between a strong FAQ match (≥0.80) and a no-match question (<0.35) is the core demo.

**`sentence-transformers` over API embeddings**
`all-MiniLM-L6-v2` runs locally, has no cost, and adds no API latency for demo scale. The model is initialized once and reused across ingest and retrieval via a module-level singleton.

**FAQ direct return at high similarity**
When the top FAQ cosine similarity exceeds 0.85, the stored answer is returned directly — no LLM generation. This is the fastest, highest-confidence path and makes the FAQ exact-match case visually distinct in the UI.

---

## Project structure

```
store-knowledge-agent/
├── main.py                     # FastAPI app, all routes
├── ingest/
│   └── store_ingest.py         # Parse store JSON, build ChromaDB collections
├── retrieval/
│   ├── classifier.py           # Rule-based + LLM fallback question classifier
│   └── retriever.py            # Route retrieval to right collection(s)
├── agent/
│   ├── answer.py               # Generate answer from retrieved chunks
│   └── confidence.py           # Confidence scoring: hit rate + hedge detection
├── intelligence/
│   └── missing_info.py         # Log unanswered questions, cluster topics
├── models/
│   ├── store.py                # Product, Policy, FAQ dataclasses
│   └── response.py             # ChatResponse, ConfidenceScore, MissingInfoReport
├── llm/
│   └── client.py               # OpenRouter wrapper
├── static/
│   ├── index.html              # Two-panel UI
│   └── app.js                  # Fetch calls and DOM rendering
├── sample_data/
│   └── sample_store.json       # Synthetic outdoor gear store with intentional gaps
├── requirements.txt
└── .env.example
```

---

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/load-store` | Load store JSON, ingest into ChromaDB |
| `POST` | `/api/chat` | Shopper question → answer + confidence + sources |
| `GET`  | `/api/missing-info` | All logged unanswered questions |
| `POST` | `/api/cluster-gaps` | LLM topic clustering of unanswered questions |
| `GET`  | `/api/health` | Health check |

---

## Intentional knowledge gaps (these surface in the dashboard)

The sample store data is designed with four gaps that will generate low-confidence signals:

- **Canada shipping** — policy explicitly states no Canada shipping but no FAQ entry exists
- **Supplement safety during pregnancy** — no medical guidance exists in the knowledge base
- **Returns past 30 days** — policy says 30-day window; a question about 6 weeks will hedge
- **Waterproof ratings** — no product mentions a waterproof rating (mm H₂O); such questions get low retrieval scores
