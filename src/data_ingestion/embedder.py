"""
Embedder using Google Gemini API
Generates 768-dimensional embeddings for text chunks
"""

import logging
from typing import List, Dict, Any
import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiEmbedder:
    """
    Text embedder using Google Gemini Text Embeddings
    Generates 768-dimensional vectors for semantic search
    """

    def __init__(self, api_key: str, model: str = "text-embedding-004"):
        """
        Initialize Gemini embedder

        Args:
            api_key: Google API key
            model: Embedding model name (default: text-embedding-004)
        """
        self.api_key = api_key
        self.model = model
        genai.configure(api_key=api_key)

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for single text

        Args:
            text: Text to embed

        Returns:
            List of 768 float values representing the embedding
        """
        try:
            result = genai.embed_content(
                model=f"models/{self.model}",
                content=text,
                task_type="RETRIEVAL_DOCUMENT",
            )

            embedding = result["embedding"]
            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = []

        try:
            # Batch process texts
            for i, text in enumerate(texts):
                if i % 10 == 0:
                    logger.info(f"Embedding text {i + 1}/{len(texts)}")

                embedding = self.embed_text(text)
                embeddings.append(embedding)

            logger.info(f"Successfully generated {len(embeddings)} embeddings")
            return embeddings

        except Exception as e:
            logger.error(f"Error in batch embedding: {str(e)}")
            raise

    def embed_chunks(
        self, chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for document chunks

        Args:
            chunks: List of chunk dictionaries with 'text' field

        Returns:
            List of chunks with added 'embedding' field
        """
        try:
            texts = [chunk.get("text", "") for chunk in chunks]
            embeddings = self.embed_batch(texts)

            # Add embeddings to chunks
            for chunk, embedding in zip(chunks, embeddings):
                chunk["embedding"] = embedding

            return chunks

        except Exception as e:
            logger.error(f"Error embedding chunks: {str(e)}")
            raise

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this model

        Returns:
            Embedding dimension (768 for text-embedding-004)
        """
        return 768
