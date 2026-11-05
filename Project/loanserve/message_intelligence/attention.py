"""Scaled dot-product attention in NumPy for the extractive summariser."""

import numpy as np


def stable_softmax(scores):
    shifted = np.asarray(scores, dtype=float) - np.max(scores, axis=-1, keepdims=True)
    exponents = np.exp(shifted)
    return exponents / exponents.sum(axis=-1, keepdims=True)


def attention_scores(queries, keys):
    queries = np.asarray(queries, dtype=float)
    keys = np.asarray(keys, dtype=float)
    return queries @ keys.T / np.sqrt(queries.shape[-1])


def scaled_dot_product_attention(queries, keys, values, allowed=None):
    scores = attention_scores(queries, keys)
    if allowed is not None:
        mask = np.asarray(allowed, dtype=bool)
        if np.any(~mask.all(axis=-1)) and np.any(~mask.any(axis=-1)):
            raise ValueError("Every query must have at least one allowed key")
        scores = np.where(mask, scores, -np.inf)
    weights = stable_softmax(scores)
    return weights @ np.asarray(values), weights
