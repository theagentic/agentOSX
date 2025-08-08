"""
SQLite-backed vector store (stubbed with LIKE search for demo; not a true vector DB).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from ..memory import VectorStore


class SQLiteVectorStore(VectorStore):
    def __init__(self, db_path: str = "./data/agentos.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                metadata TEXT
            )
            """
        )
        self.conn.commit()

    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, any]]] = None) -> List[str]:
        cur = self.conn.cursor()
        ids: List[str] = []
        for i, text in enumerate(texts):
            doc_id = f"doc_{i}_{abs(hash(text)) % 10_000_000}"
            meta = metadatas[i] if metadatas and i < len(metadatas) else {}
            cur.execute(
                "INSERT OR REPLACE INTO documents (id, text, metadata) VALUES (?, ?, ?)",
                (doc_id, text, str(meta))
            )
            ids.append(doc_id)
        self.conn.commit()
        return ids

    def similarity_search(self, query: str, k: int = 5) -> List[Tuple[str, Dict[str, any], float]]:
        # Not a real vector search; use LIKE for demo purposes
        cur = self.conn.cursor()
        cur.execute("SELECT id, text, metadata FROM documents WHERE text LIKE ? LIMIT ?", (f"%{query}%", k))
        results: List[Tuple[str, Dict[str, any], float]] = []
        for row in cur.fetchall():
            doc_id, text, metadata = row
            results.append((doc_id, {"text": text, "metadata": metadata}, 0.5))
        return results

