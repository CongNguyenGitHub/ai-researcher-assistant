"""
Main Streamlit application entry point for Context-Aware Research Assistant.

Multi-page app structure:
- Page 1: Document Processing - Upload and index documents
- Page 2: Research Queries - Perform research queries with multi-source retrieval
- Page 3: Conversation History - View and manage conversation context
- Page 4: Entity Browser - Explore extracted entities and relationships
"""

import streamlit as st
from pathlib import Path
import sys

# Add src directory to path for imports
src_path = Path(__file__).parent
sys.path.insert(0, str(src_path))

from logging_config import configure_logging, get_logger

# Configure logging on app startup
configure_logging()
logger = get_logger(__name__)


def init_session_state():
    """Initialize Streamlit session state variables."""
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.documents = []
        st.session_state.conversation_history = []
        st.session_state.entities = {}
        st.session_state.current_page = "document_processing"
        logger.info("Session state initialized")


def main():
    """Main Streamlit app function."""
    st.set_page_config(
        page_title="Context-Aware Research Assistant",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    init_session_state()
    
    # Sidebar navigation
    st.sidebar.title("Context-Aware Research Assistant")
    page = st.sidebar.radio(
        "Navigate to:",
        [
            "📁 Document Processing",
            "🔍 Research Queries",
            "💬 Conversation History",
            "🏷️ Entity Browser"
        ]
    )
    
    # Page routing
    if page == "📁 Document Processing":
        logger.debug("Navigating to Document Processing page")
        try:
            from pages.document_processing import render_document_processing
            render_document_processing()
        except Exception as e:
            st.error(f"Error loading Document Processing page: {str(e)}")
            logger.error(f"Failed to load document_processing page: {e}", exc_info=True)
    
    elif page == "🔍 Research Queries":
        logger.debug("Navigating to Research Queries page")
        st.warning("Research Queries page coming soon...")
        st.info(
            "This page will allow you to perform research queries using:\n"
            "- Document retrieval from indexed knowledge base\n"
            "- Web search via Firecrawl\n"
            "- Academic papers via arXiv\n"
            "- CrewAI agents for synthesis"
        )
    
    elif page == "💬 Conversation History":
        logger.debug("Navigating to Conversation History page")
        st.warning("Conversation History page coming soon...")
        st.info("This page will display your conversation context and memory.")
    
    elif page == "🏷️ Entity Browser":
        logger.debug("Navigating to Entity Browser page")
        st.warning("Entity Browser page coming soon...")
        st.info("This page will let you explore extracted entities and relationships.")
    
    # Sidebar info
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        ### About
        A context-aware research assistant that combines:
        - 📄 Document processing and indexing
        - 🔍 Multi-source retrieval (docs, web, papers)
        - 🤖 AI synthesis with CrewAI agents
        - 💾 Conversation memory with Zep
        """
    )
    
    logger.info(f"Rendered page: {page}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error("An unexpected error occurred. Please check the logs.")
        logger.error("Unhandled exception in main app", exc_info=True)
