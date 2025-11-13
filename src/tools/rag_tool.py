"""
RAG tool for retrieving context from indexed documents (Milvus).

Implements semantic search over uploaded and indexed documents.
"""

from typing import List, Optional
import time

from models.query import Query
from models.context import ContextChunk, SourceType
from tools.base import ToolBase, ToolResult, ToolStatus
from logging_config import get_logger

logger = get_logger(__name__)


class RAGTool(ToolBase):
    """
    Retrieval-Augmented Generation tool using Milvus vector database.
    
    Retrieves relevant document chunks from indexed documents based on
    semantic similarity to the query.
    """
    
    def __init__(
        self,
        milvus_host: str = "localhost",
        milvus_port: int = 19530,
        collection_name: str = "documents",
        embedding_dim: int = 768,
        timeout_seconds: float = 7.0,
        top_k: int = 5,
    ):
        """
        Initialize RAG tool.
        
        Args:
            milvus_host: Milvus server host
            milvus_port: Milvus server port
            collection_name: Milvus collection name
            embedding_dim: Embedding dimension (768 for Gemini)
            timeout_seconds: Query timeout in seconds
            top_k: Number of top results to return
        """
        super().__init__(timeout_seconds=timeout_seconds)
        
        self.milvus_host = milvus_host
        self.milvus_port = milvus_port
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self.top_k = top_k
        
        self._milvus_client = None
        self._embedder = None
        
        logger.info(
            f"RAGTool initialized: {milvus_host}:{milvus_port}, "
            f"collection={collection_name}, top_k={top_k}"
        )
    
    @property
    def source_type(self) -> SourceType:
        """Source type for this tool."""
        return SourceType.RAG
    
    @property
    def tool_name(self) -> str:
        """Human-readable tool name."""
        return "RAG (Document Retrieval)"
    
    def _initialize_milvus(self):
        """Initialize Milvus connection (lazy loading)."""
        if self._milvus_client is not None:
            return
        
        try:
            from pymilvus import Collection, connections
            
            # Connect to Milvus
            connections.connect(
                alias="default",
                host=self.milvus_host,
                port=self.milvus_port,
                timeout=self.timeout_seconds,
            )
            
            # Get collection
            self._milvus_client = Collection(self.collection_name)
            logger.info(f"Connected to Milvus collection: {self.collection_name}")
            
        except ImportError:
            logger.error("pymilvus not installed, cannot initialize RAGTool")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {str(e)}")
            raise
    
    def _initialize_embedder(self):
        """Initialize embedder for query encoding."""
        if self._embedder is not None:
            return
        
        try:
            from data_ingestion import GeminiEmbedder
            from config import get_config
            
            config = get_config()
            self._embedder = GeminiEmbedder(
                api_key=config.gemini.api_key,
                model=config.gemini.embedding_model,
                dimension=config.gemini.embedding_dimensions,
            )
            logger.debug("Embedder initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedder: {str(e)}")
            raise
    
    def execute(self, query: Query) -> ToolResult:
        """
        Retrieve relevant document chunks from Milvus.
        
        Args:
            query: The query to retrieve context for
            
        Returns:
            ToolResult with retrieved chunks
        """
        start_time = time.time()
        
        try:
            # Validate query
            if not self.validate_query(query):
                return self.create_error_result(
                    ToolStatus.ERROR,
                    (time.time() - start_time) * 1000,
                    "Invalid query"
                )
            
            # Initialize connections
            self._initialize_milvus()
            self._initialize_embedder()
            
            # Embed query
            logger.debug(f"Embedding query: {query.text[:100]}...")
            query_embedding = self._embedder.embed_query(query.text)
            
            # Search Milvus
            logger.debug(f"Searching Milvus with k={self.top_k}")
            results = self._milvus_client.search(
                data=[query_embedding],
                anns_field="embedding",
                param={"metric_type": "L2", "params": {"nprobe": 10}},
                limit=self.top_k,
                output_fields=["document_id", "chunk_text", "metadata"],
            )
            
            # Convert results to ContextChunks
            chunks = []
            if results and results[0]:
                for hit in results[0]:
                    # Extract metadata
                    entity = hit.entity
                    
                    chunk = self.create_chunk(
                        text=entity.get("chunk_text", ""),
                        source_id=entity.get("document_id", "unknown"),
                        source_title=entity.get("metadata", {}).get("filename", "Document"),
                        source_url=None,
                        source_date=None,
                        semantic_relevance=1 - hit.distance,  # Convert distance to similarity
                        source_reputation=0.8,  # RAG documents are indexed by users
                        recency_score=0.7,  # Average recency
                        metadata={
                            "collection": self.collection_name,
                            "distance": hit.distance,
                        }
                    )
                    chunks.append(chunk)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            logger.info(
                f"RAG retrieval complete: {len(chunks)} chunks, "
                f"time={execution_time_ms:.0f}ms"
            )
            
            return self.create_success_result(chunks, execution_time_ms)
            
        except TimeoutError:
            return self.create_error_result(
                ToolStatus.TIMEOUT,
                (time.time() - start_time) * 1000,
                f"RAG search timed out after {self.timeout_seconds}s"
            )
        
        except Exception as e:
            logger.error(f"RAG tool error: {str(e)}", exc_info=True)
            return self.create_error_result(
                ToolStatus.ERROR,
                (time.time() - start_time) * 1000,
                f"RAG retrieval failed: {str(e)}"
            )
