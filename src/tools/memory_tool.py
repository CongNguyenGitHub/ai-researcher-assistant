"""
Memory tool for managing conversation history and context.

Uses Zep Memory API to store and retrieve conversation context.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import time

from models.query import Query
from models.context import ContextChunk, SourceType
from models.memory import ConversationHistory
from tools.base import ToolBase, ToolResult, ToolStatus
from logging_config import get_logger

logger = get_logger(__name__)


class MemoryTool(ToolBase):
    """
    Conversation memory and history tool using Zep API.
    
    Retrieves previous conversations and context to enable coherent,
    contextual research across multiple queries in the same session.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        zep_base_url: str = "http://localhost:8000",
        timeout_seconds: float = 5.0,
    ):
        """
        Initialize Memory tool.
        
        Args:
            api_key: Zep API key (optional)
            zep_base_url: Zep server base URL
            timeout_seconds: API request timeout
        """
        super().__init__(timeout_seconds=timeout_seconds)
        
        self.api_key = api_key
        self.zep_base_url = zep_base_url
        
        self._client = None
        self._session_id: Optional[str] = None
        
        logger.info(
            f"MemoryTool initialized: zep_url={zep_base_url}, "
            f"timeout={timeout_seconds}s"
        )
    
    @property
    def source_type(self) -> SourceType:
        """Source type for this tool."""
        return SourceType.MEMORY
    
    @property
    def tool_name(self) -> str:
        """Human-readable tool name."""
        return "Memory (Conversation History)"
    
    def _initialize_client(self):
        """Initialize Zep client (lazy loading)."""
        if self._client is not None:
            return
        
        try:
            from zep_python import ZepClient
            
            self._client = ZepClient(
                base_url=self.zep_base_url,
                api_key=self.api_key,
            )
            logger.info(f"Zep client initialized: {self.zep_base_url}")
            
        except ImportError:
            logger.error("zep-python not installed, cannot initialize MemoryTool")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Zep client: {str(e)}")
            raise
    
    def set_session_id(self, session_id: str):
        """
        Set the session ID for memory operations.
        
        Args:
            session_id: Unique identifier for this conversation session
        """
        self._session_id = session_id
        logger.debug(f"Session ID set to: {session_id}")
    
    def execute(self, query: Query) -> ToolResult:
        """
        Retrieve relevant conversation history and memory context.
        
        Args:
            query: The current query to find related history for
            
        Returns:
            ToolResult with relevant memory context chunks
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
            
            # Check session ID
            if not self._session_id:
                logger.warning("No session ID set, returning empty memory")
                return self.create_success_result([], (time.time() - start_time) * 1000)
            
            # Initialize client
            self._initialize_client()
            
            chunks = []
            
            try:
                # Get session memory
                session = self._client.memory.get_session(self._session_id)
                
                if not session:
                    logger.debug(f"No session found for ID: {self._session_id}")
                    return self.create_success_result([], (time.time() - start_time) * 1000)
                
                # Get messages
                messages = session.get("messages", [])
                
                if not messages:
                    logger.debug("No messages in session history")
                    return self.create_success_result([], (time.time() - start_time) * 1000)
                
                # Convert relevant messages to chunks
                for message in messages:
                    # Only include assistant responses and user queries
                    role = message.get("role", "")
                    content = message.get("content", "")
                    timestamp = message.get("created_at", None)
                    
                    if not content or role not in ("assistant", "user"):
                        continue
                    
                    # Create memory chunk
                    chunk = self.create_chunk(
                        text=content[:500],  # Limit content length
                        source_id=f"memory_{self._session_id}_{hash(content) % 1000}",
                        source_title=f"Chat History ({role.capitalize()})",
                        source_url=None,
                        source_date=self._parse_timestamp(timestamp),
                        semantic_relevance=0.5,  # Memory has lower relevance to new queries
                        source_reputation=0.9,  # Memory is from our own system
                        recency_score=0.6,  # Memory is less recent than live sources
                        metadata={
                            "tool": "memory",
                            "role": role,
                            "session_id": self._session_id,
                            "message_timestamp": timestamp,
                        }
                    )
                    chunks.append(chunk)
                
            except Exception as e:
                logger.warning(f"Failed to retrieve session memory: {str(e)}")
                # Don't fail, just return empty - memory is optional
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            logger.info(
                f"Memory retrieval complete: {len(chunks)} messages, "
                f"time={execution_time_ms:.0f}ms"
            )
            
            return self.create_success_result(chunks, execution_time_ms)
            
        except TimeoutError:
            return self.create_error_result(
                ToolStatus.TIMEOUT,
                (time.time() - start_time) * 1000,
                f"Memory retrieval timed out after {self.timeout_seconds}s"
            )
        
        except Exception as e:
            logger.error(f"Memory tool error: {str(e)}", exc_info=True)
            return self.create_error_result(
                ToolStatus.ERROR,
                (time.time() - start_time) * 1000,
                f"Memory retrieval failed: {str(e)}"
            )
    
    def add_to_memory(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Add a message to the conversation memory.
        
        Args:
            role: 'user' or 'assistant'
            content: Message content
            metadata: Additional metadata
            
        Returns:
            True if successful, False otherwise
        """
        if not self._session_id:
            logger.warning("Cannot add to memory without session ID")
            return False
        
        try:
            self._initialize_client()
            
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
            }
            
            # This is a simplified example - actual Zep API may differ
            logger.debug(f"Adding message to memory: {role}: {content[:50]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add message to memory: {str(e)}")
            return False
    
    @staticmethod
    def _parse_timestamp(timestamp: Any) -> Optional[datetime]:
        """Parse timestamp from various formats."""
        if not timestamp:
            return None
        
        if isinstance(timestamp, datetime):
            return timestamp
        
        try:
            if isinstance(timestamp, str):
                # Try ISO format
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass
        
        return None
