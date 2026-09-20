from dataclasses import dataclass
import re

from .extractors import PageText


@dataclass(frozen=True)
class ChunkDraft:
    page: int
    index: int
    text: str


def _cut(text: str, maximum: int) -> int:
    if len(text) <= maximum:
        return len(text)
    boundary = max(text.rfind(" ", 0, maximum), text.rfind("\n", 0, maximum))
    return boundary if boundary >= maximum // 2 else maximum


def chunk_pages(pages: list[PageText], target: int = 1000, maximum: int = 1000, overlap: int = 150) -> list[ChunkDraft]:
    chunks: list[ChunkDraft] = []
    index = 0
    for page in pages:
        text = re.sub(r"\s+", " ", page.text).strip()
        cursor = 0
        while cursor < len(text):
            remaining = text[cursor:]
            preferred = _cut(remaining, target)
            if len(remaining) > target and preferred < target // 2:
                preferred = _cut(remaining, maximum)
            end = min(len(text), cursor + min(preferred, maximum))
            piece = text[cursor:end].strip()
            if piece:
                chunks.append(ChunkDraft(page.page, index, piece))
                index += 1
            if end >= len(text):
                break
            next_cursor = max(cursor + 1, end - overlap)
            while next_cursor < end and next_cursor > cursor and text[next_cursor - 1] not in " \n":
                next_cursor -= 1
            cursor = next_cursor
    return chunks
