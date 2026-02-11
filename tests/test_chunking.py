import pytest

from app.rag.chunking import chunk_text


def test_chunking_produces_multiple_chunks_with_overlap() -> None:
    text = "A" * 1200
    chunks = chunk_text(text=text, chunk_size=300, overlap=50)

    assert len(chunks) >= 4
    for i in range(1, len(chunks)):
        assert chunks[i].start_char <= chunks[i - 1].end_char
        assert chunks[i].start_char >= chunks[i - 1].end_char - 60


def test_chunking_handles_small_text() -> None:
    chunks = chunk_text(text="Hello world", chunk_size=500, overlap=50)
    assert len(chunks) == 1
    assert chunks[0].text == "Hello world"


def test_chunking_empty_text_returns_empty_list() -> None:
    assert chunk_text(text="   ", chunk_size=500, overlap=50) == []


def test_chunking_invalid_parameters_raise() -> None:
    with pytest.raises(ValueError):
        chunk_text(text="abc", chunk_size=0, overlap=0)
    with pytest.raises(ValueError):
        chunk_text(text="abc", chunk_size=10, overlap=10)
