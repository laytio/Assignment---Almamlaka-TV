import hashlib


def create_chunks(documents: list[dict]) -> list[dict]:
    """
    Convert extracted PDF pages into page-level chunks.

    Each page becomes one chunk.
    """

    chunks = []

    for document in documents:

        source = document["source"]
        page = document["page"]
        text = document["text"]

        # Generate a deterministic chunk ID
        unique_string = f"{source}:{page}:{text}"

        chunk_id = hashlib.sha256(
            unique_string.encode("utf-8")
        ).hexdigest()[:16]

        chunks.append({
            "chunk_id": chunk_id,
            "source": source,
            "page": page,
            "text": text
        })

    return chunks