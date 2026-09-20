import fitz
import pytest


def make_pdf(*pages: str) -> bytes:
    document = fitz.open()
    for text in pages:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    result = document.tobytes()
    document.close()
    return result


def test_pdf_extraction_preserves_pages():
    from app.extractors import extract_document

    pages = extract_document(make_pdf("Premiere page", "Deuxieme page"), "application/pdf")

    assert [(page.page, page.text.strip()) for page in pages] == [
        (1, "Premiere page"),
        (2, "Deuxieme page"),
    ]


def test_pdf_without_text_explains_ocr_limit():
    from app.extractors import DocumentExtractionError, extract_document

    with pytest.raises(DocumentExtractionError, match="OCR"):
        extract_document(make_pdf(""), "application/pdf")


def test_chunks_never_cross_page_boundaries():
    from app.chunking import chunk_pages
    from app.extractors import PageText

    chunks = chunk_pages([
        PageText(1, "Alpha " * 220),
        PageText(2, "Beta " * 220),
    ])

    assert all(len(chunk.text) <= 1000 for chunk in chunks)
    assert all(("Alpha" in chunk.text) != ("Beta" in chunk.text) for chunk in chunks)
    assert {chunk.page for chunk in chunks} == {1, 2}


def test_typical_page_stays_in_one_chunk():
    from app.chunking import chunk_pages
    from app.extractors import PageText

    chunks = chunk_pages([PageText(1, "Politique interne détaillée. " * 28)])

    assert len(chunks) == 1


def test_markdown_is_extracted_as_single_page():
    from app.extractors import extract_document

    pages = extract_document("# Politique\nTélétravail deux jours.".encode(), "text/markdown")

    assert pages[0].page == 1
    assert "Télétravail" in pages[0].text
