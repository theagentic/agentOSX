"""
Conversation memory and artifact registry.
- Short-term buffer with summarization stub
- Long-term vector interface backed by stores
- Artifact registry for tool outputs
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple

from ..llm.base import Message, Role


@dataclass
class Artifact:
    id: str
    path: str
    type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class VectorStore(Protocol):
    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        ...

    def similarity_search(self, query: str, k: int = 5) -> List[Tuple[str, Dict[str, Any], float]]:
        ...


class Memory:
    """Short-term conversation buffer and long-term vector memory."""

    def __init__(self, vector_store: Optional[VectorStore] = None, artifact_dir: str = "./data/artifacts"):
        self.buffer: List[Message] = []
        self.max_buffer_messages: int = 25
        self.vector_store = vector_store
        self.artifact_dir = Path(artifact_dir)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_index_path = self.artifact_dir / "artifacts.json"
        self._artifacts: Dict[str, Artifact] = {}
        self._load_artifacts()

    def add_message(self, message: Message):
        self.buffer.append(message)
        if len(self.buffer) > self.max_buffer_messages:
            self._summarize_buffer()

    def get_context(self) -> List[Message]:
        return self.buffer[-self.max_buffer_messages :]

    def _summarize_buffer(self):
        # Stub: drop oldest; real impl would summarize with LLM
        if self.buffer:
            self.buffer = self.buffer[-self.max_buffer_messages :]

    # Vector memory
    def add_knowledge(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        if not self.vector_store:
            return []
        return self.vector_store.add_texts(texts, metadatas)

    def search_knowledge(self, query: str, k: int = 5) -> List[Tuple[str, Dict[str, Any], float]]:
        if not self.vector_store:
            return []
        return self.vector_store.similarity_search(query, k)

    # Artifacts
    def register_artifact(self, path: str, type: str, metadata: Optional[Dict[str, Any]] = None) -> Artifact:
        art = Artifact(id=str(uuid.uuid4()), path=path, type=type, metadata=metadata or {})
        self._artifacts[art.id] = art
        self._save_artifacts()
        return art

    def list_artifacts(self) -> List[Artifact]:
        return list(self._artifacts.values())

    def _save_artifacts(self):
        try:
            with open(self.artifacts_index_path, "w") as f:
                json.dump({k: asdict(v) for k, v in self._artifacts.items()}, f, indent=2)
        except Exception:
            pass

    def _load_artifacts(self):
        if not self.artifacts_index_path.exists():
            return
        try:
            data = json.loads(self.artifacts_index_path.read_text())
            self._artifacts = {k: Artifact(**v) for k, v in data.items()}
        except Exception:
            self._artifacts = {}

