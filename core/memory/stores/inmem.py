"""
In-memory vector store for testing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

from ..memory import VectorStore


def _simple_embed(text: str) -> Dict[str, float]:
    """Very naive bag-of-words embedding for demo purposes."""
    vec: Dict[str, float] = {}
    for token in text.lower().split():
        vec[token] = vec.get(token, 0.0) + 1.0
    return vec


def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    dot = sum(a.get(k, 0.0) * v for k, v in b.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class InMemoryVectorStore(VectorStore):
    def __init__(self):
        self.docs: List[Tuple[str, str, Dict[str, float], Dict[str, any]]] = []

    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, any]]] = None) -> List[str]:
        ids: List[str] = []
        for i, text in enumerate(texts):
            meta = metadatas[i] if metadatas and i < len(metadatas) else {}
            vec = _simple_embed(text)
            doc_id = f"mem_{len(self.docs)}"
            self.docs.append((doc_id, text, vec, meta))
            ids.append(doc_id)
        return ids

    def similarity_search(self, query: str, k: int = 5) -> List[Tuple[str, Dict[str, any], float]]:
        qvec = _simple_embed(query)
        scored = []
        for doc_id, text, vec, meta in self.docs:
            s = _cosine(qvec, vec)
            scored.append((doc_id, meta | {"text": text}, s))
        scored.sort(key=lambda x: x[2], reverse=True)
        return scored[:k]

