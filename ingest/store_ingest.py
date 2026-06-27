import json
import uuid
from typing import Optional

from sentence_transformers import SentenceTransformer

from models.store import FAQEntry, PolicySection, Product, ProductVariant, StoreKnowledge

_embedder: Optional[SentenceTransformer] = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _product_to_text(product: Product) -> str:
    text = (
        f"{product.name}. {product.description} "
        f"Price: ${product.price:.2f}. Category: {product.category}. "
        f"Materials: {', '.join(product.materials)}. "
        f"Tags: {', '.join(product.tags)}."
    )
    if product.care_instructions:
        text += f" Care: {product.care_instructions}"
    variant_sizes = list({v.size for v in product.variants if v.size})
    variant_colors = list({v.color for v in product.variants if v.color})
    if variant_sizes:
        text += f" Available sizes: {', '.join(variant_sizes)}."
    if variant_colors:
        text += f" Available colors: {', '.join(variant_colors)}."
    return text


def ingest_store(store: StoreKnowledge, chroma_client) -> dict:
    embedder = get_embedder()

    # Products collection
    products_col = chroma_client.get_or_create_collection(
        f"products_{store.store_id}",
        metadata={"hnsw:space": "cosine"},
    )
    product_texts = [_product_to_text(p) for p in store.products]
    product_embeddings = embedder.encode(product_texts).tolist()
    products_col.add(
        ids=[p.product_id for p in store.products],
        embeddings=product_embeddings,
        documents=product_texts,
        metadatas=[
            {
                "product_id": p.product_id,
                "name": p.name,
                "price": p.price,
                "category": p.category,
            }
            for p in store.products
        ],
    )

    # Policies collection
    policies_col = chroma_client.get_or_create_collection(
        f"policies_{store.store_id}",
        metadata={"hnsw:space": "cosine"},
    )
    policy_texts = [p.content for p in store.policies]
    policy_embeddings = embedder.encode(policy_texts).tolist()
    policies_col.add(
        ids=[p.policy_id for p in store.policies],
        embeddings=policy_embeddings,
        documents=policy_texts,
        metadatas=[
            {
                "policy_id": p.policy_id,
                "category": p.category,
                "title": p.title,
            }
            for p in store.policies
        ],
    )

    # FAQs collection — embed question, store answer in metadata
    faqs_col = chroma_client.get_or_create_collection(
        f"faq_{store.store_id}",
        metadata={"hnsw:space": "cosine"},
    )
    faq_question_texts = [f.question for f in store.faqs]
    faq_embeddings = embedder.encode(faq_question_texts).tolist()
    faqs_col.add(
        ids=[f.faq_id for f in store.faqs],
        embeddings=faq_embeddings,
        documents=faq_question_texts,
        metadatas=[
            {
                "faq_id": f.faq_id,
                "question": f.question,
                "answer": f.answer,
            }
            for f in store.faqs
        ],
    )

    return {
        "store_id": store.store_id,
        "products_ingested": len(store.products),
        "policies_ingested": len(store.policies),
        "faqs_ingested": len(store.faqs),
    }


def load_store_from_json(path: str) -> StoreKnowledge:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    products = []
    for p in data.get("products", []):
        variants = [
            ProductVariant(
                size=v.get("size"),
                color=v.get("color"),
                sku=v.get("sku", str(uuid.uuid4())[:8]),
                in_stock=v.get("in_stock", True),
            )
            for v in p.get("variants", [])
        ]
        products.append(
            Product(
                product_id=p.get("product_id", str(uuid.uuid4())),
                name=p["name"],
                description=p["description"],
                price=float(p["price"]),
                category=p.get("category", "general"),
                tags=p.get("tags", []),
                materials=p.get("materials", []),
                variants=variants,
                care_instructions=p.get("care_instructions"),
            )
        )

    policies = [
        PolicySection(
            policy_id=p.get("policy_id", str(uuid.uuid4())),
            category=p["category"],
            title=p["title"],
            content=p["content"],
        )
        for p in data.get("policies", [])
    ]

    faqs = [
        FAQEntry(
            faq_id=f.get("faq_id", str(uuid.uuid4())),
            question=f["question"],
            answer=f["answer"],
            tags=f.get("tags", []),
        )
        for f in data.get("faqs", [])
    ]

    return StoreKnowledge(
        store_id=data.get("store_id", str(uuid.uuid4())),
        store_name=data["store_name"],
        products=products,
        policies=policies,
        faqs=faqs,
    )
