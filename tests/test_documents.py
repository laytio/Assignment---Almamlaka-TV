from backend.app.document_loader import load_all_pdfs
from backend.app.chunking import create_chunks


def test_pdf_extraction():
    documents = load_all_pdfs("backend/data")

    assert len(documents) == 6

    assert len(set(doc["source"] for doc in documents)) == 3

    for doc in documents:
        assert doc["text"].strip()
        assert doc["page"] in (1, 2)


def test_chunking_metadata():
    documents = load_all_pdfs("backend/data")
    chunks = create_chunks(documents)

    assert len(chunks) == 6

    for chunk in chunks:
        assert "chunk_id" in chunk
        assert "source" in chunk
        assert "page" in chunk
        assert "text" in chunk


def test_unique_chunk_ids():
    documents = load_all_pdfs("backend/data")
    chunks = create_chunks(documents)

    ids = [chunk["chunk_id"] for chunk in chunks]

    assert len(ids) == len(set(ids))


def test_deterministic_chunking():
    documents = load_all_pdfs("backend/data")

    first_run = create_chunks(documents)
    second_run = create_chunks(documents)

    assert first_run == second_run


def test_chunk_provenance():
    documents = load_all_pdfs("backend/data")
    chunks = create_chunks(documents)

    original_pages = {
        (doc["source"], doc["page"]): doc["text"]
        for doc in documents
    }

    for chunk in chunks:
        key = (chunk["source"], chunk["page"])

        assert key in original_pages
        assert chunk["text"] == original_pages[key]