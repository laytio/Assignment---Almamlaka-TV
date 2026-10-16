from backend.app.document_loader import load_all_pdfs


def build_full_context(data_dir: str = "backend/data") -> str:
    """
    Build a full context from all PDF documents,
    preserving source filenames and page numbers.
    """

    documents = load_all_pdfs(data_dir)

    context_parts = []

    for doc in documents:
        source = doc["source"]
        page = doc["page"]
        text = doc["text"]

        section = (
            f"[SOURCE: {source} | PAGE: {page}]\n"
            f"{text}\n"
            f"[/SOURCE]"
        )

        context_parts.append(section)

    return "\n\n".join(context_parts)