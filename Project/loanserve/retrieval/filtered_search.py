"""Narrow policy retrieval to the named product and general rules."""

import re

from loanserve.retrieval.vector_store import search_policy


GENERAL_POLICY = "all"
PRODUCT_WORDS = {
    "home": ("home loan", "housing", "home loans"),
    "vehicle": ("vehicle", "car loan", "two wheeler", "two-wheeler", "auto loan"),
    "gold": ("gold", "ornament", "jewellery", "pledged"),
    "personal": ("personal loan", "personal loans"),
}


def product_in_question(question):
    lowered = question.lower()
    for product, words in PRODUCT_WORDS.items():
        if any(re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", lowered) for word in words):
            return product
    return GENERAL_POLICY


def policy_filter(product_type):
    if product_type == GENERAL_POLICY:
        return {"product_type": GENERAL_POLICY}
    return {"product_type": {"$in": [product_type, GENERAL_POLICY]}}


def filtered_search(collection, question, embedder, how_many):
    return search_policy(collection, question, embedder, how_many,
                         where=policy_filter(product_in_question(question)))
