"""
Data Ingestion Pipeline
Orchestrates document parsing, embedding, and vector database loading
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.data_ingestion.parser import TensorLakeDocumentParser, ParsedDocument
from src.data_ingestion.embedder import GeminiEmbedder
from src.data_ingestion.milvus_loader import MilvusLoader

logger = logging.getLogger(__name__)


class DataIngestionPipeline:
    """
    End-to-end data ingestion pipeline
    Converts documents → chunks → embeddings → vector database
    """

    def __init__(
        self,
        tensorlake_api_key: str,
        tensorlake_base_url: str,
        gemini_api_key: str,
        gemini_model: str,
        milvus_host: str = "localhost",
        milvus_port: int = 19530,
        milvus_user: str = "default",
        milvus_password: str = "Milvus",
        collection_name: str = "documents",
    ):
        """
        Initialize data ingestion pipeline

        Args:
            tensorlake_api_key: TensorLake API key
            tensorlake_base_url: TensorLake base URL
            gemini_api_key: Google Gemini API key
            gemini_model: Gemini embedding model
            milvus_host: Milvus server host
            milvus_port: Milvus server port
            milvus_user: Milvus user
            milvus_password: Milvus password
            collection_name: Milvus collection name
        """
        self.parser = TensorLakeDocumentParser(tensorlake_api_key, tensorlake_base_url)
        self.embedder = GeminiEmbedder(gemini_api_key, gemini_model)
        self.loader = MilvusLoader(
            collection_name=collection_name,
            host=milvus_host,
            port=milvus_port,
            user=milvus_user,
            password=milvus_password,
        )

        # Ensure collection is created
        embedding_dim = self.embedder.get_embedding_dimension()
        self.loader.create_collection(dimension=embedding_dim)

    def process_document(
        self,
        file_path: str,
        document_id: Optional[str] = None,
        chunk_size: int = 512,
        overlap: int = 64,
    ) -> Dict[str, Any]:
        """
        Process a single document through the entire pipeline

        Args:
            file_path: Path to document file
            document_id: Optional document identifier
            chunk_size: Chunk size in tokens
            overlap: Chunk overlap in tokens

        Returns:
            Dictionary with processing results
        """
        logger.info(f"Starting pipeline for document: {file_path}")

        try:
            # Step 1: Parse document
            logger.info("Step 1: Parsing document with TensorLake...")
            parsed_doc: ParsedDocument = self.parser.parse_document(
                file_path,
                document_id=document_id,
                chunk_size=chunk_size,
                overlap=overlap,
            )

            if parsed_doc.parsing_status != "success":
                logger.error(f"Parsing failed: {parsed_doc.error_message}")
                return {
                    "status": "failed",
                    "stage": "parsing",
                    "error": parsed_doc.error_message,
                    "document_id": parsed_doc.document_id,
                    "filename": parsed_doc.filename,
                }

            logger.info(f"  ✓ Parsed {len(parsed_doc.chunks)} chunks")

            # Step 2: Generate embeddings
            logger.info("Step 2: Generating embeddings with Gemini...")
            embedded_chunks = self.embedder.embed_chunks(parsed_doc.chunks)
            logger.info(f"  ✓ Generated {len(embedded_chunks)} embeddings")

            # Step 3: Load into Milvus
            logger.info("Step 3: Loading vectors into Milvus...")
            inserted_count = self.loader.insert_chunks(
                embedded_chunks,
                document_id=parsed_doc.document_id,
                filename=parsed_doc.filename,
            )
            logger.info(f"  ✓ Inserted {inserted_count} vectors")

            return {
                "status": "success",
                "document_id": parsed_doc.document_id,
                "filename": parsed_doc.filename,
                "chunks_parsed": len(parsed_doc.chunks),
                "embeddings_generated": len(embedded_chunks),
                "vectors_inserted": inserted_count,
            }

        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}")
            return {
                "status": "failed",
                "stage": "pipeline",
                "error": str(e),
                "document_id": document_id or file_path,
                "filename": Path(file_path).name,
            }

    def process_batch(
        self,
        file_paths: List[str],
        chunk_size: int = 512,
        overlap: int = 64,
    ) -> List[Dict[str, Any]]:
        """
        Process multiple documents through the pipeline

        Args:
            file_paths: List of document file paths
            chunk_size: Chunk size in tokens
            overlap: Chunk overlap in tokens

        Returns:
            List of processing results for each document
        """
        logger.info(f"Starting batch processing for {len(file_paths)} documents")

        results = []
        for i, file_path in enumerate(file_paths, 1):
            logger.info(f"Processing [{i}/{len(file_paths)}] {file_path}")
            result = self.process_document(file_path, chunk_size=chunk_size, overlap=overlap)
            results.append(result)

            # Log progress
            if result["status"] == "success":
                logger.info(
                    f"  SUCCESS: {result['chunks_parsed']} chunks, "
                    f"{result['vectors_inserted']} vectors inserted"
                )
            else:
                logger.warning(f"  FAILED: {result.get('error', 'Unknown error')}")

        # Summary
        successful = sum(1 for r in results if r["status"] == "success")
        failed = len(results) - successful
        total_vectors = sum(
            r.get("vectors_inserted", 0) for r in results if r["status"] == "success"
        )

        logger.info(
            f"Batch processing complete: {successful} successful, "
            f"{failed} failed, {total_vectors} total vectors inserted"
        )

        return results

    def process_directory(
        self,
        directory: str,
        patterns: List[str] = None,
        chunk_size: int = 512,
        overlap: int = 64,
    ) -> List[Dict[str, Any]]:
        """
        Process all documents in a directory

        Args:
            directory: Path to directory containing documents
            patterns: File patterns to match (default: common document formats)
            chunk_size: Chunk size in tokens
            overlap: Chunk overlap in tokens

        Returns:
            List of processing results
        """
        if patterns is None:
            patterns = ["*.pdf", "*.docx", "*.txt", "*.md"]

        path = Path(directory)
        file_paths = []

        for pattern in patterns:
            file_paths.extend(path.glob(pattern))

        file_paths = [str(p) for p in file_paths]
        logger.info(f"Found {len(file_paths)} documents in {directory}")

        return self.process_batch(file_paths, chunk_size=chunk_size, overlap=overlap)

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the loaded documents

        Returns:
            Collection statistics
        """
        return self.loader.get_collection_stats()

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return

        Returns:
            List of similar documents
        """
        return self.loader.search_similar(query_embedding, top_k=top_k)
