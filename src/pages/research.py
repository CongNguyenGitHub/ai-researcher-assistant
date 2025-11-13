"""
Research Query page for Streamlit application.

Allows users to submit research queries and receive synthesized answers
from multiple sources (RAG, web, arxiv, memory).
"""

import streamlit as st
import time
from datetime import datetime

from models.query import Query
from models.memory import ConversationHistory, UserPreferences
from services.orchestrator import Orchestrator
from services.evaluator import Evaluator
from services.synthesizer import Synthesizer
from utils.formatters import format_response
from logging_config import get_logger

logger = get_logger(__name__)


def render_research_query():
    """Render the research query page."""
    st.title("🔍 Research Queries")
    st.markdown(
        "Enter your research question and get synthesized answers from multiple sources."
    )
    
    # Initialize session state
    if "orchestrator" not in st.session_state:
        try:
            st.session_state.orchestrator = initialize_orchestrator()
        except Exception as e:
            st.error(f"Failed to initialize orchestrator: {str(e)}")
            logger.error(f"Orchestrator initialization failed: {e}", exc_info=True)
            return
    
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = ConversationHistory(
            user_id="default_user",
            session_id=st.session_state.get("session_id", "default_session"),
        )
    
    # Sidebar: User preferences
    with st.sidebar:
        st.markdown("### User Preferences")
        response_format = st.selectbox(
            "Response Format",
            ["detailed", "concise", "technical", "narrative"],
            help="How detailed should responses be?"
        )
        
        max_response_length = st.slider(
            "Max Response Length (chars)",
            500, 10000, 5000, 100,
            help="Maximum length of generated responses"
        )
        
        information_depth = st.selectbox(
            "Information Depth",
            ["overview", "comprehensive", "expert"],
            help="How deep should the analysis be?"
        )
        
        preferred_sources = st.multiselect(
            "Preferred Sources",
            ["rag", "arxiv", "web", "memory"],
            default=["rag", "arxiv", "web"],
            help="Which sources to prioritize"
        )
    
    # Main query input
    col1, col2 = st.columns([0.85, 0.15])
    
    with col1:
        query_text = st.text_area(
            "Enter your research question",
            height=100,
            placeholder="e.g., What are the latest developments in quantum computing?",
            help="Be specific for better results"
        )
    
    with col2:
        submit_button = st.button("🚀 Submit", use_container_width=True)
    
    # Query submission
    if submit_button and query_text:
        process_query(
            query_text,
            response_format=response_format,
            information_depth=information_depth,
            max_response_length=max_response_length,
            preferred_sources=preferred_sources,
        )
    elif submit_button and not query_text:
        st.warning("Please enter a research question")
    
    # Display conversation history
    with st.expander("📜 Conversation History", expanded=False):
        if st.session_state.conversation_history.messages:
            for i, msg in enumerate(st.session_state.conversation_history.messages):
                if msg.role.value == "user":
                    st.markdown(f"**You:** {msg.content}")
                else:
                    st.markdown(f"**Assistant:** {msg.content[:200]}...")
                    if len(msg.content) > 200:
                        st.caption(f"View full response above")
        else:
            st.info("No conversation history yet")


def initialize_orchestrator():
    """
    Initialize the Orchestrator with evaluator and synthesizer.
    
    Returns:
        Configured Orchestrator instance
    """
    evaluator = Evaluator(
        quality_threshold=0.6,
        dedup_threshold=0.9,
        max_age_days=365,
    )
    
    synthesizer = Synthesizer(
        model_name="gemini-2.0-flash",
        max_response_length=5000,
    )
    
    orchestrator = Orchestrator(
        evaluator=evaluator,
        synthesizer=synthesizer,
        tools=[],  # Tools will be added in Phase 4
        max_workers=4,
    )
    
    logger.info("Orchestrator initialized with evaluator and synthesizer")
    return orchestrator


def process_query(
    query_text: str,
    response_format: str = "detailed",
    information_depth: str = "comprehensive",
    max_response_length: int = 5000,
    preferred_sources: list = None,
):
    """
    Process a user research query.
    
    Args:
        query_text: The query text
        response_format: Response format preference
        information_depth: Depth of analysis
        max_response_length: Max response length
        preferred_sources: Preferred source types
    """
    if preferred_sources is None:
        preferred_sources = ["rag", "arxiv", "web"]
    
    # Create Query object
    query = Query(
        user_id="default_user",
        session_id=st.session_state.conversation_history.session_id,
        text=query_text,
        topic_category="general",
    )
    
    # Display processing indicator
    with st.spinner("🔍 Searching sources..."):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Mark as processing
            query.mark_processing()
            progress_bar.progress(0.2)
            status_text.text("Retrieving context from 4 sources...")
            
            # For MVP: Skip actual retrieval (tools not yet implemented)
            # In Phase 4, this will call orchestrator with real tools
            time.sleep(1)  # Simulate processing
            progress_bar.progress(0.5)
            status_text.text("Evaluating context quality...")
            
            time.sleep(1)  # Simulate evaluation
            progress_bar.progress(0.75)
            status_text.text("Synthesizing response...")
            
            # For MVP: Create mock response
            from models.response import FinalResponse
            response = FinalResponse(
                query_id=query.id,
                user_id=query.user_id,
                session_id=query.session_id,
                answer=(
                    f"Based on the query '{query_text}', I found relevant information across multiple sources. "
                    f"The research assistant is currently in MVP mode - full multi-source retrieval will be enabled in Phase 4. "
                    f"Current capabilities include: document indexing via TensorLake, embedding generation with Gemini, "
                    f"semantic search in Milvus, and response synthesis with citations."
                ),
                overall_confidence=0.75,
            )
            response.generation_time_ms = 1500
            
            progress_bar.progress(1.0)
            status_text.text("✅ Complete!")
            time.sleep(0.5)
            progress_bar.empty()
            status_text.empty()
            
            # Display response
            display_response(response)
            
            # Update conversation memory
            st.session_state.conversation_history.add_message(
                st.session_state.conversation_history.Message(
                    role="user",
                    content=query_text,
                )
            )
            st.session_state.conversation_history.add_message(
                st.session_state.conversation_history.Message(
                    role="assistant",
                    content=response.answer,
                    metadata={"confidence": response.overall_confidence},
                )
            )
            
            logger.info(f"Query processed successfully: {query.id}")
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"Error processing query: {str(e)}")
            query.mark_failed(str(e))
            logger.error(f"Query processing failed: {e}", exc_info=True)


def display_response(response):
    """
    Display a FinalResponse with formatting.
    
    Args:
        response: FinalResponse to display
    """
    # Main answer
    st.markdown("### 📝 Answer")
    st.markdown(response.answer)
    
    # Confidence indicator
    col1, col2, col3 = st.columns(3)
    with col1:
        confidence_pct = int(response.overall_confidence * 100)
        st.metric("Confidence", f"{confidence_pct}%")
    with col2:
        st.metric("Generation Time", f"{response.generation_time_ms:.0f}ms")
    with col3:
        st.metric("Sources Used", len(response.sources))
    
    # Sections
    if response.sections:
        st.markdown("### 🔑 Key Points")
        for section in response.sections:
            with st.expander(f"{section.heading} ({int(section.confidence*100)}% confidence)"):
                st.markdown(section.content)
    
    # Perspectives (if contradictions)
    if response.perspectives:
        st.markdown("### ⚠️ Multiple Perspectives Detected")
        for i, perspective in enumerate(response.perspectives, 1):
            col1, col2 = st.columns([0.8, 0.2])
            with col1:
                st.markdown(f"**View {i}**: {perspective.viewpoint}")
            with col2:
                st.caption(f"{int(perspective.confidence*100)}%")
    
    # Sources
    if response.sources:
        st.markdown("### 📚 Sources")
        for source in response.sources:
            col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
            with col1:
                if source.url:
                    st.markdown(f"[{source.title}]({source.url})")
                else:
                    st.markdown(source.title)
            with col2:
                st.caption(f"{source.type.upper()}")
            with col3:
                st.caption(f"{int(source.relevance*100)}% relevant")
    
    # Response metadata
    with st.expander("ℹ️ Response Details"):
        st.json(response.to_dict())
    
    # Export options
    col1, col2, col3 = st.columns(3)
    with col1:
        markdown_text = format_response(response, format_type="markdown")
        st.download_button(
            "📄 Download as Markdown",
            markdown_text,
            "response.md",
            "text/markdown",
        )
    with col2:
        json_text = format_response(response, format_type="json")
        st.download_button(
            "📋 Download as JSON",
            json_text,
            "response.json",
            "application/json",
        )
    with col3:
        citations_text = format_response(response, format_type="inline_citations")
        st.download_button(
            "🔗 Download with Citations",
            citations_text,
            "response_citations.txt",
            "text/plain",
        )


# Export for app.py
def render_research_processing():
    """Render function for app.py."""
    render_research_query()
