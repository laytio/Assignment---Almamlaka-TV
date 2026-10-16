import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """
    Generate embeddings and perform semantic search
    over document chunks.
    """

    def __init__(self):
        self.model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            device="cpu"
        )

        self.chunks = []
        self.embeddings = None

    def index_chunks(self, chunks: list):
        """
        Generate embeddings for document chunks.
        """

        self.chunks = chunks

        if not chunks:
            self.embeddings = None
            return

        texts = [
            chunk["text"]
            for chunk in chunks
        ]

        self.embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True
        )

    def search(self, query: str, top_k: int = 3):
        """
        Find the most relevant document chunks
        using cosine similarity.
        """

        if self.embeddings is None:
            raise ValueError(
                "No documents indexed. Call index_chunks() first."
            )

        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
            convert_to_numpy=True
        )[0]

        # Embeddings are normalized, so dot product
        # is equivalent to cosine similarity.
        scores = np.dot(
            self.embeddings,
            query_embedding
        )

        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []

        for index in top_indices:
            chunk = self.chunks[int(index)]

            results.append({
                "source": chunk["source"],
                "page": chunk["page"],
                "text": chunk["text"],
                "score": float(scores[index])
            })

        return results