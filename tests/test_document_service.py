import pytest

from app.services.document_service import create_document_record, get_document, index_document


def test_index_document_transitions_statuses(tmp_path, monkeypatch) -> None:
    # Settings are already monkeypatched via autouse fixture in conftest; this test just verifies behavior.
    doc = create_document_record(filename="a.txt", content=b"Hello world")
    assert doc.status == "queued"
    assert doc.chunk_count == 0

    indexed = index_document(doc.id)
    assert indexed.status == "indexed"
    assert indexed.chunk_count >= 1
    assert indexed.indexed_at is not None
    assert indexed.error_message is None

    reloaded = get_document(doc.id)
    assert reloaded is not None
    assert reloaded.status == "indexed"


def test_index_document_failure_sets_failed_status() -> None:
    doc = create_document_record(filename="b.txt", content=b"will fail")

    # Simulate missing stored file.
    from app.config import get_settings

    settings = get_settings()
    stored_path = settings.upload_path / doc.stored_filename
    stored_path.unlink()

    failed = index_document(doc.id)
    assert failed.status == "failed"
    assert failed.error_message is not None

