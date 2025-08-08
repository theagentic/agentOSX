"""
ChromaDB-backed vector store wrapper (optional dependency).
Falls back gracefully if chromadb is not installed.
"""
from __future__ import annotations

from typing import Dict, List, Tuple, Optional

try:
    import chromadb  # type: ignore
except Exception:  # pragma: no cover - optional dep
    chromadb = None

from ..memory import VectorStore


class ChromaVectorStore(VectorStore):
    def __init__(self, collection: str = "agentos", persist_dir: str = "./data/chroma"):
        if chromadb is None:
            raise ImportError("chromadb is not installed. Install with pip install chromadb")
        self.client = chromadb.HttpClient() if hasattr(chromadb, "HttpClient") else chromadb.Client(
            settings={"chroma_db_impl": "duckdb+parquet", "persist_directory": persist_dir}
        )
        self.collection = self.client.get_or_create_collection(collection)

    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, any]]] = None) -> List[str]:
        ids = [f"ch_{i}" for i in range(len(texts))]
        self.collection.add(ids=ids, documents=texts, metadatas=metadatas or [{} for _ in texts])
        return ids

    def similarity_search(self, query: str, k: int = 5) -> List[Tuple[str, Dict[str, any], float]]:
        res = self.collection.query(query_texts=[query], n_results=k)
        out: List[Tuple[str, Dict[str, any], float]] = []
        for i in range(len(res.get("ids", [[]])[0])):
            out.append((res["ids"][0][i], res["metadatas"][0][i] | {"text": res["documents"][0][i]}, res["distances"][0][i]))
        return out

