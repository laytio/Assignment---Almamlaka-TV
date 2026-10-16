from app.document_loader import load_all_pdfs
from app.chunking import create_chunks
from app.embedding_service import EmbeddingService
from app.llm_service import generate_grounded_response

class RAGService:
    """
    Retrieval-Augmented Generation service.

    Combines:
    - PDF loading
    - Document chunking
    - Semantic retrieval
    - Grounded answer generation
    """

    def __init__(self, data_dir="backend/data"):

        # Load PDF documents
        documents = load_all_pdfs(data_dir)

        # Create chunks
        self.chunks = create_chunks(documents)

        # Initialize embedding model
        self.embedding_service = EmbeddingService()

        # Generate embeddings once
        self.embedding_service.index_chunks(self.chunks)

    def retrieve(self, question: str, top_k: int = 3):
        """
        Retrieve the most relevant document chunks.
        """

        return self.embedding_service.search(
            query=question,
            top_k=top_k
        )

    def build_context(self, retrieved_chunks: list):
        """
        Build context with source citations.
        """

        context_parts = []

        for chunk in retrieved_chunks:

            source = chunk["source"]
            page = chunk["page"]
            text = chunk["text"]

            context_parts.append(
                f"[SOURCE: {source} | PAGE: {page}]\n"
                f"{text}\n"
                f"[/SOURCE]"
            )

        return "\n\n".join(context_parts)

    def ask(
        self,
        question: str,
        conversation_history: list | None = None,
        top_k: int = 3
    ):
        """
        Retrieve relevant context and generate an answer.
        """

        # Step 1: Retrieve
        retrieved_chunks = self.retrieve(
            question=question,
            top_k=top_k
        )

        # Step 2: Build context
        context = self.build_context(retrieved_chunks)

        # Step 3: Generate grounded answer
        answer = generate_grounded_response(
            question=question,
            context=context,
            conversation_history=conversation_history
        )

        return {
            "question": question,
            "answer": answer,
            "sources": [
                {
                    "source": chunk["source"],
                    "page": chunk["page"],
                    "score": chunk["score"]
                }
                for chunk in retrieved_chunks
            ]
        }