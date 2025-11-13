"""
Milvus vector database loader
Handles insertion of embeddings and metadata into Milvus
"""

import logging
from typing import List, Dict, Any, Optional
from pymilvus import Collection, DataType, FieldSchema, CollectionSchema, connections

logger = logging.getLogger(__name__)


class MilvusLoader:
    """
    Vector database loader for Milvus
    Manages collection creation and vector insertion
    """

    def __init__(
        self,
        collection_name: str = "documents",
        host: str = "localhost",
        port: int = 19530,
        user: str = "default",
        password: str = "Milvus",
    ):
        """
        Initialize Milvus loader

        Args:
            collection_name: Name of Milvus collection
            host: Milvus server host
            port: Milvus server port
            user: Milvus user
            password: Milvus password
        """
        self.collection_name = collection_name
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.collection = None

        # Connect to Milvus
        self._connect()

    def _connect(self):
        """Connect to Milvus server"""
        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
            )
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {str(e)}")
            raise

    def create_collection(self, dimension: int = 768):
        """
        Create or get collection with proper schema

        Args:
            dimension: Embedding dimension (default: 768)
        """
        try:
            # Check if collection exists
            if self.collection_name not in self._list_collections():
                logger.info(f"Creating collection: {self.collection_name}")

                # Define fields
                fields = [
                    FieldSchema(
                        name="id",
                        dtype=DataType.INT64,
                        description="Primary key",
                        is_primary=True,
                        auto_id=True,
                    ),
                    FieldSchema(
                        name="embedding",
                        dtype=DataType.FLOAT_VECTOR,
                        description="Embedding vector",
                        dim=dimension,
                    ),
                    FieldSchema(
                        name="text",
                        dtype=DataType.VARCHAR,
                        description="Chunk text",
                        max_length=65535,
                    ),
                    FieldSchema(
                        name="document_id",
                        dtype=DataType.VARCHAR,
                        description="Source document ID",
                        max_length=256,
                    ),
                    FieldSchema(
                        name="chunk_id",
                        dtype=DataType.VARCHAR,
                        description="Chunk identifier",
                        max_length=256,
                    ),
                    FieldSchema(
                        name="filename",
                        dtype=DataType.VARCHAR,
                        description="Source filename",
                        max_length=512,
                    ),
                    FieldSchema(
                        name="page_number",
                        dtype=DataType.INT32,
                        description="Page number (if applicable)",
                    ),
                    FieldSchema(
                        name="chunk_type",
                        dtype=DataType.VARCHAR,
                        description="Type of chunk (text, table, image, etc.)",
                        max_length=64,
                    ),
                ]

                schema = CollectionSchema(
                    fields=fields,
                    description="Collection for RAG embeddings",
                    enable_dynamic_field=True,
                )

                self.collection = Collection(
                    name=self.collection_name,
                    schema=schema,
                )

                # Create index
                self._create_index()
                logger.info(f"Collection {self.collection_name} created successfully")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
                self.collection = Collection(self.collection_name)

        except Exception as e:
            logger.error(f"Error creating collection: {str(e)}")
            raise

    def _create_index(self):
        """Create index for embedding field"""
        try:
            index_params = {
                "index_type": "IVF_FLAT",
                "metric_type": "L2",
                "params": {"nlist": 128},
            }

            self.collection.create_index(
                field_name="embedding",
                index_params=index_params,
            )
            logger.info("Created IVF_FLAT index on embedding field")
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
            raise

    def insert_chunks(
        self, chunks: List[Dict[str, Any]], document_id: str, filename: str
    ) -> int:
        """
        Insert chunks with embeddings into Milvus

        Args:
            chunks: List of chunks with 'text', 'embedding', and metadata
            document_id: Document identifier
            filename: Source filename

        Returns:
            Number of inserted records
        """
        try:
            # Ensure collection is loaded
            if self.collection is None:
                self.create_collection()

            self.collection.load()

            # Prepare data for insertion
            data = {
                "embedding": [],
                "text": [],
                "document_id": [],
                "chunk_id": [],
                "filename": [],
                "page_number": [],
                "chunk_type": [],
            }

            for chunk in chunks:
                embedding = chunk.get("embedding")
                if embedding is None:
                    logger.warning(f"Chunk {chunk.get('chunk_id')} missing embedding")
                    continue

                data["embedding"].append(embedding)
                data["text"].append(chunk.get("text", ""))
                data["document_id"].append(document_id)
                data["chunk_id"].append(chunk.get("chunk_id", ""))
                data["filename"].append(filename)
                data["page_number"].append(chunk.get("page_number", -1))
                data["chunk_type"].append(chunk.get("type", "text"))

            if not data["embedding"]:
                logger.warning("No embeddings to insert")
                return 0

            # Insert data
            result = self.collection.insert(data)
            inserted_count = result.insert_count

            logger.info(f"Inserted {inserted_count} chunks into {self.collection_name}")
            return inserted_count

        except Exception as e:
            logger.error(f"Error inserting chunks: {str(e)}")
            raise

    def search_similar(
        self, query_embedding: List[float], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in the collection

        Args:
            query_embedding: Query embedding vector
            top_k: Number of top results to return

        Returns:
            List of similar documents with metadata
        """
        try:
            # Ensure collection is loaded
            if self.collection is None:
                raise ValueError("Collection not initialized")

            self.collection.load()

            # Prepare search parameters
            search_params = {"metric_type": "L2", "params": {"nprobe": 10}}

            # Execute search
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["text", "document_id", "filename", "chunk_id", "page_number"],
            )

            # Format results
            formatted_results = []
            for hit in results[0]:
                formatted_results.append(
                    {
                        "distance": hit.distance,
                        "text": hit.entity.get("text", ""),
                        "document_id": hit.entity.get("document_id", ""),
                        "filename": hit.entity.get("filename", ""),
                        "chunk_id": hit.entity.get("chunk_id", ""),
                        "page_number": hit.entity.get("page_number", -1),
                    }
                )

            return formatted_results

        except Exception as e:
            logger.error(f"Error searching collection: {str(e)}")
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics

        Returns:
            Dictionary with collection stats
        """
        try:
            if self.collection is None:
                return {}

            return {
                "name": self.collection.name,
                "num_rows": self.collection.num_entities,
                "fields": [f.name for f in self.collection.schema.fields],
            }

        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {}

    def _list_collections(self) -> List[str]:
        """List all collections in Milvus"""
        try:
            return [col for col in connections.list_collections()]
        except Exception as e:
            logger.error(f"Error listing collections: {str(e)}")
            return []

    def disconnect(self):
        """Disconnect from Milvus"""
        try:
            connections.disconnect(alias="default")
            logger.info("Disconnected from Milvus")
        except Exception as e:
            logger.error(f"Error disconnecting: {str(e)}")
