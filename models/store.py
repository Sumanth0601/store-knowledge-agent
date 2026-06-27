from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ProductVariant:
    size: Optional[str]
    color: Optional[str]
    sku: str
    in_stock: bool


@dataclass
class Product:
    product_id: str
    name: str
    description: str
    price: float
    category: str
    tags: List[str]
    materials: List[str]
    variants: List[ProductVariant]
    care_instructions: Optional[str]


@dataclass
class PolicySection:
    policy_id: str
    category: str  # "returns", "shipping", "warranty"
    title: str
    content: str


@dataclass
class FAQEntry:
    faq_id: str
    question: str
    answer: str
    tags: List[str]


@dataclass
class StoreKnowledge:
    store_id: str
    store_name: str
    products: List[Product]
    policies: List[PolicySection]
    faqs: List[FAQEntry]
