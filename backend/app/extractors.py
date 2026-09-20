from dataclasses import dataclass
import re

import fitz


class DocumentExtractionError(ValueError):
    pass


@dataclass(frozen=True)
class PageText:
    page: int
    text: str


def _clean(text: str) -> str:
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract_document(data: bytes, mime_type: str) -> list[PageText]:
    if mime_type == "application/pdf":
        try:
            document = fitz.open(stream=data, filetype="pdf")
        except Exception as exc:
            raise DocumentExtractionError("Le fichier PDF est invalide") from exc
        try:
            pages = [PageText(number, _clean(page.get_text("text", sort=True))) for number, page in enumerate(document, 1)]
        finally:
            document.close()
        if not any(page.text for page in pages):
            raise DocumentExtractionError("Ce PDF ne contient pas de texte exploitable. L'OCR n'est pas pris en charge.")
        return pages
    if mime_type in {"text/plain", "text/markdown"}:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DocumentExtractionError("Le fichier texte doit être encodé en UTF-8") from exc
        text = _clean(text)
        if not text:
            raise DocumentExtractionError("Le document est vide")
        return [PageText(1, text)]
    raise DocumentExtractionError("Type de fichier non pris en charge")
