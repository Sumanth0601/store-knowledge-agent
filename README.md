# Store Knowledge Agent

Most store chatbots just answer questions. This one also tracks the questions it *couldn't* answer — and tells the merchant what to fix.

It's a two-panel demo: a shopper chat on the left, and a live "Missing Intelligence" dashboard on the right. Every time the agent gives a low-confidence answer, it shows up on the right with a timestamp and confidence score. Hit "Cluster Gaps" and it groups them into themes with plain-English recommendations.

![Overview](static/screenshots/overview.png)

The sample store is a fictional outdoor gear brand (Alpine Gear Co.) with products, a return policy, FAQs, and a few intentional blind spots — Canada shipping, supplement safety during pregnancy, returns past 30 days. Those are the ones that surface as gaps.

---

## Getting started

You'll need a free [OpenRouter](https://openrouter.ai/keys) API key. It uses free models — no credit card needed.

```bash
git clone https://github.com/Sumanth0601/store-knowledge-agent
cd store-knowledge-agent

pip install -r requirements.txt

cp .env.example .env
# Add your OpenRouter API key to .env

uvicorn main:app --reload
# Open http://localhost:8000
```

Click **Load Store**, then start asking questions.

---

## Try these questions

These are designed to show the full range of the system:

| Question | What happens |
|----------|-------------|
| "Does the Alpine jacket run true to size?" | Answered from product info |
| "What's your return policy?" | Full policy retrieved and summarised |
| "Do you ship to Canada?" | Answered — policy explicitly says no |
| "Is the protein powder safe during pregnancy?" | No info exists → flagged as gap immediately |
| "Can I return a jacket I bought 6 weeks ago?" | Agent hedges → low confidence → flagged |

After asking a few, click **Cluster Gaps** on the right to group the unanswered questions and get recommendations.

- **Canada shipping** — policy explicitly states no Canada shipping but no FAQ entry exists
- **Supplement safety during pregnancy** — no medical guidance exists in the knowledge base
- **Returns past 30 days** — policy says 30-day window; a question about 6 weeks will hedge
- **Waterproof ratings** — no product mentions a waterproof rating (mm H₂O); such questions get low retrieval scores
