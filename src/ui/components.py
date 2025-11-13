"""
UI components for Context-Aware Research Assistant.

Reusable Streamlit components for displaying responses and metrics.
"""

import streamlit as st
from typing import Dict, List, Any, Optional
from models.response import FinalResponse
from models.context import FilteredContext


def display_response_card(response: FinalResponse, compact: bool = False):
    """
    Display a response in card format.
    
    Args:
        response: FinalResponse to display
        compact: If True, show condensed version
    """
    with st.container():
        # Header
        cols = st.columns([0.7, 0.15, 0.15])
        with cols[0]:
            st.markdown(f"### {response.answer[:100]}...")
        with cols[1]:
            confidence = int(response.overall_confidence * 100)
            st.metric("Confidence", f"{confidence}%")
        with cols[2]:
            st.metric("Sources", len(response.sources))
        
        # Content
        if not compact:
            st.markdown(response.answer)
            
            # Key points
            if response.sections:
                st.markdown("**Key Points:**")
                for section in response.sections[:3]:
                    st.markdown(f"- {section.heading}: {section.content[:100]}...")
        
        # Quality indicators
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption(f"⏱️ {response.generation_time_ms:.0f}ms")
        with col2:
            status = "✅ High" if response.overall_confidence > 0.7 else "⚠️ Medium" if response.overall_confidence > 0.5 else "❌ Low"
            st.caption(f"Quality: {status}")
        with col3:
            if response.response_quality.has_contradictions:
                st.caption("⚠️ Contradictions detected")
            else:
                st.caption("✓ Consistent sources")


def display_confidence_gauge(confidence: float, size: str = "default"):
    """
    Display confidence as a gauge.
    
    Args:
        confidence: Confidence value (0-1)
        size: Gauge size ("small", "default", "large")
    """
    percentage = int(confidence * 100)
    
    if confidence >= 0.8:
        color = "green"
        emoji = "✅"
    elif confidence >= 0.6:
        color = "blue"
        emoji = "✓"
    elif confidence >= 0.4:
        color = "orange"
        emoji = "⚠️"
    else:
        color = "red"
        emoji = "❌"
    
    st.markdown(
        f"<div style='background-color: {color}20; padding: 10px; border-radius: 5px;'>"
        f"{emoji} <b>Confidence: {percentage}%</b></div>",
        unsafe_allow_html=True
    )


def display_source_attribution(sources: List, title: str = "Sources"):
    """
    Display source attributions in a table.
    
    Args:
        sources: List of SourceAttribution objects
        title: Section title
    """
    if not sources:
        st.info("No sources used")
        return
    
    st.markdown(f"### {title}")
    
    # Create table data
    table_data = []
    for source in sources:
        table_data.append({
            "Title": source.title,
            "Type": source.type.upper(),
            "Relevance": f"{int(source.relevance*100)}%",
            "URL": source.url if source.url else "—"
        })
    
    st.table(table_data)


def display_contradiction_warning(response: FinalResponse):
    """
    Display warning about contradictory information.
    
    Args:
        response: FinalResponse with potential contradictions
    """
    if not response.response_quality.has_contradictions:
        return
    
    with st.warning("⚠️ **Contradictory Information Detected**"):
        st.markdown(
            "The sources provide conflicting information about this topic. "
            "Review all perspectives before drawing conclusions."
        )
        
        if response.perspectives:
            st.markdown("### Alternative Perspectives:")
            for i, perspective in enumerate(response.perspectives, 1):
                col1, col2 = st.columns([0.8, 0.2])
                with col1:
                    st.markdown(f"**{i}. {perspective.viewpoint}**")
                    st.caption(perspective.summary)
                with col2:
                    st.metric("Support", f"{int(perspective.weight*100)}%")


def display_filtering_summary(filtered_context: Optional[FilteredContext]):
    """
    Display context filtering summary.
    
    Args:
        filtered_context: FilteredContext with filtering stats
    """
    if not filtered_context:
        return
    
    with st.expander("📊 Filtering Statistics"):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Original Chunks",
                filtered_context.original_chunk_count
            )
        with col2:
            st.metric(
                "Filtered Chunks",
                filtered_context.filtered_chunk_count
            )
        with col3:
            removal_rate = (
                (filtered_context.original_chunk_count - filtered_context.filtered_chunk_count) /
                max(filtered_context.original_chunk_count, 1) * 100
            )
            st.metric("Removal Rate", f"{removal_rate:.0f}%")
        with col4:
            st.metric(
                "Avg Quality",
                f"{filtered_context.average_quality_score:.2f}"
            )
        
        if filtered_context.contradictions_detected:
            st.warning(f"🔍 {len(filtered_context.contradictions_detected)} contradictions detected")
        
        if filtered_context.removed_chunks:
            with st.expander("Removed Chunks"):
                for record in filtered_context.removed_chunks[:5]:
                    st.caption(f"**{record.reason.value}**: {record.text_preview}...")


def display_section_breakdown(sections: List, max_sections: int = 5):
    """
    Display response sections in expandable format.
    
    Args:
        sections: List of ResponseSection objects
        max_sections: Maximum sections to display
    """
    if not sections:
        st.info("No sections in response")
        return
    
    st.markdown("### Key Points")
    
    for section in sections[:max_sections]:
        confidence = int(section.confidence * 100)
        
        with st.expander(
            f"📌 {section.heading} ({confidence}% confidence)",
            expanded=(section.order == 0)
        ):
            st.markdown(section.content)
            
            if section.sources:
                st.caption(f"Sources: {', '.join(section.sources)}")


def display_response_metadata(response: FinalResponse):
    """
    Display response metadata and quality metrics.
    
    Args:
        response: FinalResponse to display metadata for
    """
    with st.expander("ℹ️ Response Metadata"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Response ID", response.id[:8] + "...")
            st.metric("Query ID", response.query_id[:8] + "...")
        
        with col2:
            st.metric("Generation Time", f"{response.generation_time_ms:.0f}ms")
            st.metric("Overall Confidence", f"{int(response.overall_confidence*100)}%")
        
        with col3:
            st.metric("Completeness", f"{int(response.response_quality.completeness*100)}%")
            st.metric("Informativeness", f"{int(response.response_quality.informativeness*100)}%")
        
        # Quality assessment
        st.markdown("**Quality Assessment:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if response.response_quality.has_contradictions:
                st.warning("Contains contradictions")
            else:
                st.success("No contradictions detected")
        
        with col2:
            if response.response_quality.degraded_mode:
                st.warning("Generated in degraded mode")
            else:
                st.success("Full data available")
        
        with col3:
            if response.overall_confidence > 0.7:
                st.success("High confidence")
            elif response.overall_confidence > 0.5:
                st.info("Medium confidence")
            else:
                st.warning("Low confidence")


def display_retrieval_status(sources_consulted: List[str], sources_failed: List[str]):
    """
    Display status of source retrieval.
    
    Args:
        sources_consulted: List of successful sources
        sources_failed: List of failed sources
    """
    with st.container():
        st.markdown("### 📡 Source Status")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"✅ **Retrieved ({len(sources_consulted)})**")
            if sources_consulted:
                for source in sources_consulted:
                    st.caption(f"  • {source.upper()}")
            else:
                st.caption("  No sources retrieved")
        
        with col2:
            if sources_failed:
                st.markdown(f"❌ **Failed ({len(sources_failed)})**")
                for source in sources_failed:
                    st.caption(f"  • {source.upper()}")
            else:
                st.markdown("❌ **Failed (0)**")
