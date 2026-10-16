from pathlib import Path
import pymupdf


def load_pdf(file_path: str) -> list[dict]:
    """
    Extract text from a PDF while preserving
    the source filename and page number.
    """

    documents = []

    with pymupdf.open(file_path) as pdf:

        for page_index, page in enumerate(pdf):

            text = page.get_text("text").strip()

            if not text:
                continue

            documents.append({
                "source": Path(file_path).name,
                "page": page_index + 1,
                "text": text
            })

    return documents 

def load_all_pdfs(directory: str) -> list[dict]:
    """
    Load all PDF files from a directory.
    """

    all_documents = []

    pdf_files = sorted(Path(directory).glob("*.pdf"))

    for pdf_file in pdf_files:
        pages = load_pdf(str(pdf_file))
        all_documents.extend(pages)

    return all_documents