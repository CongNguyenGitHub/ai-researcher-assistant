"""
Document Parser using TensorLake API
Parses documents into structured chunks with metadata preservation
"""

import json
import logging
from typing import List, Dict, Any, Optional
import requests
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ParsedDocument:
    """Represents a parsed document with chunks"""
    document_id: str
    filename: str
    source: str
    chunks: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    parsing_status: str  # "success", "partial", "failed"
    error_message: Optional[str] = None


class TensorLakeDocumentParser:
    """
    Document parser using TensorLake API
    Handles multiple document formats with intelligent chunking
    """

    def __init__(self, api_key: str, base_url: str = "https://api.tensorlake.ai"):
        """
        Initialize TensorLake document parser

        Args:
            api_key: TensorLake API key
            base_url: TensorLake API base URL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def parse_document(
        self,
        file_path: str,
        document_id: Optional[str] = None,
        chunk_size: int = 512,
        overlap: int = 64,
    ) -> ParsedDocument:
        """
        Parse a document using TensorLake API

        Args:
            file_path: Path to document file (PDF, DOCX, TXT, Markdown, etc.)
            document_id: Optional document identifier
            chunk_size: Number of tokens per chunk (default: 512)
            overlap: Token overlap between chunks (default: 64)

        Returns:
            ParsedDocument with chunks and metadata
        """
        try:
            with open(file_path, "rb") as f:
                files = {"file": f}
                data = {
                    "chunk_size": chunk_size,
                    "chunk_overlap": overlap,
                }

                response = requests.post(
                    f"{self.base_url}/parse",
                    files=files,
                    data=data,
                    headers=self.headers,
                    timeout=60,
                )

            if response.status_code != 200:
                error_msg = f"TensorLake parsing failed: {response.text}"
                logger.error(error_msg)
                return ParsedDocument(
                    document_id=document_id or file_path,
                    filename=file_path.split("/")[-1],
                    source="local",
                    chunks=[],
                    metadata={},
                    parsing_status="failed",
                    error_message=error_msg,
                )

            result = response.json()

            # Extract chunks and metadata from TensorLake response
            chunks = self._process_tensorlake_response(result)

            return ParsedDocument(
                document_id=document_id or file_path,
                filename=file_path.split("/")[-1],
                source="local",
                chunks=chunks,
                metadata={
                    "original_size": result.get("original_size"),
                    "chunk_count": len(chunks),
                    "parser": "tensorlake",
                    "chunk_size": chunk_size,
                    "overlap": overlap,
                },
                parsing_status="success",
            )

        except FileNotFoundError as e:
            logger.error(f"Document file not found: {file_path}")
            return ParsedDocument(
                document_id=document_id or file_path,
                filename=file_path.split("/")[-1],
                source="local",
                chunks=[],
                metadata={},
                parsing_status="failed",
                error_message=str(e),
            )
        except Exception as e:
            logger.error(f"Error parsing document {file_path}: {str(e)}")
            return ParsedDocument(
                document_id=document_id or file_path,
                filename=file_path.split("/")[-1],
                source="local",
                chunks=[],
                metadata={},
                parsing_status="failed",
                error_message=str(e),
            )

    def parse_batch(
        self,
        file_paths: List[str],
        chunk_size: int = 512,
        overlap: int = 64,
    ) -> List[ParsedDocument]:
        """
        Parse multiple documents

        Args:
            file_paths: List of document file paths
            chunk_size: Number of tokens per chunk
            overlap: Token overlap between chunks

        Returns:
            List of ParsedDocument objects
        """
        results = []
        for file_path in file_paths:
            logger.info(f"Parsing document: {file_path}")
            parsed = self.parse_document(file_path, chunk_size=chunk_size, overlap=overlap)
            results.append(parsed)
            logger.info(
                f"  - Status: {parsed.parsing_status}, "
                f"Chunks: {len(parsed.chunks)}"
            )
        return results

    @staticmethod
    def _process_tensorlake_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process TensorLake API response into chunk format

        Args:
            response: Raw response from TensorLake API

        Returns:
            List of chunks with text and metadata
        """
        chunks = []

        # TensorLake returns chunks with text and metadata
        for i, chunk_data in enumerate(response.get("chunks", [])):
            chunk = {
                "chunk_id": f"chunk_{i}",
                "text": chunk_data.get("text", ""),
                "metadata": chunk_data.get("metadata", {}),
                "page_number": chunk_data.get("page", None),
                "type": chunk_data.get("type", "text"),  # text, table, image, etc.
            }
            chunks.append(chunk)

        return chunks
