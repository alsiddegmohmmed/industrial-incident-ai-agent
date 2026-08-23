from pathlib import Path

from incident_agent.retrieval import ManualRepository


def test_manual_ingestion_creates_nonempty_chunks_with_stable_sources() -> None:
    repository = ManualRepository(Path("data/manuals"))

    chunks = repository.chunks()

    assert len(chunks) >= 6
    assert all(chunk.text for chunk in chunks)
    assert all(chunk.evidence_ref.startswith("manual:") for chunk in chunks)
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)


def test_retrieval_ranks_relevant_manual_passage_first() -> None:
    repository = ManualRepository(Path("data/manuals"))

    results = repository.search(
        "ACM-400",
        "rising vibration and temperature bearing problem",
        limit=3,
    )

    assert results
    assert "bearing" in results[0].chunk.text.lower()
    assert results[0].score >= results[-1].score


def test_retrieval_filters_model_and_ignores_irrelevant_query() -> None:
    repository = ManualRepository(Path("data/manuals"))

    assert repository.search("PMP-200", "bearing lubrication", limit=3) == []
    assert repository.search("UNKNOWN-999", "telemetry availability", limit=3) == []
