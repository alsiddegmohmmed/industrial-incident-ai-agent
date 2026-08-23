"""Small local manual index used by the v0.3 grounding tool.

The index deliberately stays in-process and dependency-free. It uses sparse
TF-IDF vectors and cosine similarity, which is enough to teach ingestion,
chunking, filtering, ranking, and source attribution before introducing a
database or a neural embedding service.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path


TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class ManualChunk:
    chunk_id: str
    device_model: str
    title: str
    text: str
    source_ref: str
    evidence_ref: str


@dataclass(frozen=True)
class ManualSearchResult:
    chunk: ManualChunk
    score: float


class ManualRepository:
    """Ingest Markdown manuals and return bounded ranked passages."""

    def __init__(
        self,
        manual_directory: Path,
        *,
        max_chunk_chars: int = 900,
        overlap_chars: int = 120,
        minimum_score: float = 0.08,
    ) -> None:
        if max_chunk_chars < 200:
            raise ValueError("max_chunk_chars must be at least 200")
        if overlap_chars < 0 or overlap_chars >= max_chunk_chars:
            raise ValueError("overlap_chars must be smaller than max_chunk_chars")
        self._minimum_score = minimum_score
        self._chunks = self._ingest(
            manual_directory,
            max_chunk_chars=max_chunk_chars,
            overlap_chars=overlap_chars,
        )
        if not self._chunks:
            raise ValueError(f"No manual documents found in: {manual_directory}")
        self._idf = self._build_idf(self._chunks)
        self._vectors = {
            chunk.chunk_id: self._vectorize(chunk.text) for chunk in self._chunks
        }
        self._norms = {
            chunk_id: _norm(vector) for chunk_id, vector in self._vectors.items()
        }

    def chunks(self) -> tuple[ManualChunk, ...]:
        return tuple(self._chunks)

    def search(
        self,
        device_model: str,
        query: str,
        *,
        limit: int = 3,
    ) -> list[ManualSearchResult]:
        """Return relevant chunks for one known device model."""
        normalized_model = device_model.strip().upper()
        candidates = [
            chunk for chunk in self._chunks if chunk.device_model == normalized_model
        ]
        query_vector = self._vectorize(query)
        query_norm = _norm(query_vector)
        if not candidates or not query_vector or query_norm == 0:
            return []

        ranked = []
        for chunk in candidates:
            score = _dot(query_vector, self._vectors[chunk.chunk_id]) / (
                query_norm * self._norms[chunk.chunk_id]
            )
            if score >= self._minimum_score:
                ranked.append(ManualSearchResult(chunk=chunk, score=score))
        ranked.sort(key=lambda result: (-result.score, result.chunk.chunk_id))
        return ranked[:limit]

    def _ingest(
        self,
        manual_directory: Path,
        *,
        max_chunk_chars: int,
        overlap_chars: int,
    ) -> list[ManualChunk]:
        chunks: list[ManualChunk] = []
        for path in sorted(manual_directory.glob("*")):
            if path.suffix.lower() not in {".md", ".markdown", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8")
            device_model = path.stem.upper()
            for index, (title, section_text) in enumerate(_sections(text)):
                for part_index, part in enumerate(
                    _split_text(section_text, max_chunk_chars, overlap_chars)
                ):
                    chunk_number = len(chunks)
                    chunk_id = f"{path.stem.lower()}-{chunk_number:03d}"
                    source_ref = f"{path.name}#{_slug(title)}-{part_index + 1}"
                    chunks.append(
                        ManualChunk(
                            chunk_id=chunk_id,
                            device_model=device_model,
                            title=title,
                            text=part,
                            source_ref=source_ref,
                            evidence_ref=f"manual:{device_model.lower()}:{chunk_id}",
                        )
                    )
        return chunks

    def _build_idf(self, chunks: list[ManualChunk]) -> dict[str, float]:
        document_frequency: dict[str, int] = {}
        for chunk in chunks:
            for token in set(_tokens(chunk.text)):
                document_frequency[token] = document_frequency.get(token, 0) + 1
        total_documents = len(chunks)
        return {
            token: math.log((1 + total_documents) / (1 + frequency)) + 1
            for token, frequency in document_frequency.items()
        }

    def _vectorize(self, text: str) -> dict[str, float]:
        counts: dict[str, int] = {}
        for token in _tokens(text):
            counts[token] = counts.get(token, 0) + 1
        total = sum(counts.values())
        if total == 0:
            return {}
        return {
            token: (count / total) * self._idf.get(token, 1.0)
            for token, count in counts.items()
        }


def _sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    current_title = "Manual overview"
    current_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("#"):
            if current_lines:
                sections.append((current_title, current_lines))
            current_title = line.lstrip("#").strip() or current_title
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_title, current_lines))
    return [
        (title, " ".join(line.strip() for line in lines if line.strip()))
        for title, lines in sections
        if any(line.strip() for line in lines)
    ]


def _split_text(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + max_chars, len(normalized))
        if end < len(normalized):
            boundary = normalized.rfind(" ", start, end)
            if boundary > start + max_chars // 2:
                end = boundary
        chunks.append(normalized[start:end].strip())
        if end >= len(normalized):
            break
        start = max(0, end - overlap_chars)
    return chunks


def _tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _slug(value: str) -> str:
    return "-".join(_tokens(value))[:80] or "section"


def _dot(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(token, 0.0) for token, value in left.items())


def _norm(vector: dict[str, float]) -> float:
    return math.sqrt(sum(value * value for value in vector.values()))
