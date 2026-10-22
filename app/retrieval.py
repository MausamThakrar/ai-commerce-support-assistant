
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass
class KnowledgeChunk:
    id: str
    source: str
    heading: str
    text: str


class KnowledgeRetriever:
    def __init__(self, knowledge_dir: Path = KNOWLEDGE_DIR):
        self.knowledge_dir = knowledge_dir
        self.model = SentenceTransformer(MODEL_NAME)
        self.chunks = self._load_chunks()

        if not self.chunks:
            raise ValueError("No knowledge documents found")

        self.embeddings = self.model.encode(
            [chunk.text for chunk in self.chunks],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

    def _load_chunks(self) -> list[KnowledgeChunk]:
        chunks = []

        for path in sorted(self.knowledge_dir.glob("*.md")):
            content = path.read_text(encoding="utf-8")

            heading = path.stem
            section_lines = []
            section_number = 0

            def add_section():
                nonlocal section_number

                text = "\n".join(section_lines).strip()
                if not text:
                    return

                chunks.append(
                    KnowledgeChunk(
                        id=f"{path.stem}-{section_number}",
                        source=path.name,
                        heading=heading,
                        text=f"{heading}\n{text}",
                    )
                )
                section_number += 1

            for line in content.splitlines():
                if line.startswith("## "):
                    add_section()
                    heading = line.removeprefix("## ").strip()
                    section_lines = []
                else:
                    section_lines.append(line)

            add_section()

        return chunks

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        if not query.strip():
            return []

        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )[0]

        scores = np.einsum(
            "ij,j->i",
            self.embeddings,
            query_embedding,
        )

        if not np.all(np.isfinite(scores)):
            raise ValueError(
                "Retrieval produced non-finite similarity scores"
            )

        ranked_indices = np.argsort(scores)[::-1][:top_k]

        return [
            {
                "id": self.chunks[i].id,
                "source": self.chunks[i].source,
                "heading": self.chunks[i].heading,
                "text": self.chunks[i].text,
                "score": round(float(scores[i]), 4),
            }
            for i in ranked_indices
        ]