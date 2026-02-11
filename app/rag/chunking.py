from __future__ import annotations

from app.models.schemas import Chunk


def _find_split(text: str, start: int, target_end: int, max_end: int) -> int:
    """Find a friendly split point near target_end."""
    window = text[start:max_end]
    if not window.strip():
        return max_end

    preferred_markers = ["\n\n", ". ", "\n", " "]
    for marker in preferred_markers:
        idx = text.rfind(marker, start, target_end + 1)
        if idx > start:
            if marker in {". ", " "}:
                return idx + len(marker)
            return idx

    return min(target_end, max_end)


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[Chunk]:
    """
    Split text into fixed-size chunks with overlap.

    The splitter attempts to end chunks on paragraph/sentence boundaries while
    keeping chunk size close to the configured maximum.
    """
    if not text or not text.strip():
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0:
        raise ValueError("overlap must be non-negative")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    normalized = text.replace("\r\n", "\n").strip()
    text_len = len(normalized)
    chunks: list[Chunk] = []

    start = 0
    index = 0
    while start < text_len:
        target_end = min(start + chunk_size, text_len)
        max_end = min(start + chunk_size + 100, text_len)
        if target_end == text_len:
            end = text_len
        else:
            end = _find_split(normalized, start, target_end, max_end)
        if end <= start:
            end = target_end

        chunk_text_value = normalized[start:end].strip()
        if chunk_text_value:
            chunks.append(
                Chunk(
                    text=chunk_text_value,
                    chunk_index=index,
                    start_char=start,
                    end_char=end,
                )
            )
            index += 1

        if end >= text_len:
            break

        next_start = max(0, end - overlap)
        if next_start <= start:
            next_start = end
        start = next_start

    return chunks
