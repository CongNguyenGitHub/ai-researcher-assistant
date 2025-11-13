"""
Formatters for Context-Aware Research Assistant.

Functions for formatting responses with citations and special handling for contradictions.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from models.response import FinalResponse, ResponseSection, SourceAttribution, Perspective
from models.context import FilteredContext, FilteredChunk
from logging_config import get_logger

logger = get_logger(__name__)


class ResponseFormatter:
    """Formats FinalResponse objects with citations and contradiction handling."""
    
    @staticmethod
    def to_json(response: FinalResponse, indent: int = 2) -> str:
        """
        Convert FinalResponse to JSON with all details.
        
        Args:
            response: FinalResponse to convert
            indent: JSON indentation level
            
        Returns:
            JSON string representation
        """
        return json.dumps(response.to_dict(), indent=indent, default=str)
    
    @staticmethod
    def to_markdown(response: FinalResponse) -> str:
        """
        Convert FinalResponse to formatted Markdown.
        
        Args:
            response: FinalResponse to format
            
        Returns:
            Markdown formatted response
        """
        parts = []
        
        # Main answer
        parts.append("# Answer\n")
        parts.append(response.answer)
        parts.append("")
        
        # Sections
        if response.sections:
            parts.append("## Key Points\n")
            for section in response.sections:
                parts.append(f"### {section.heading}\n")
                parts.append(section.content)
                
                # Section confidence
                confidence_pct = int(section.confidence * 100)
                parts.append(f"\n_Confidence: {confidence_pct}%_\n")
                parts.append("")
        
        # Perspectives (contradictions)
        if response.perspectives:
            parts.append("## Multiple Perspectives\n")
            parts.append("Note: Sources provide conflicting information:\n")
            for i, perspective in enumerate(response.perspectives, 1):
                parts.append(f"**Perspective {i}**: {perspective.viewpoint}")
                parts.append(f"- Sources: {', '.join(perspective.sources)}")
                confidence_pct = int(perspective.confidence * 100)
                parts.append(f"- Confidence: {confidence_pct}%\n")
        
        # Sources
        if response.sources:
            parts.append("## Sources\n")
            for source in response.sources:
                parts.append(f"- **{source.title}** ({source.type.upper()})")
                if source.url:
                    parts.append(f"  URL: {source.url}")
                confidence_pct = int(source.relevance * 100)
                parts.append(f"  Relevance: {confidence_pct}%")
                parts.append("")
        
        # Metadata
        parts.append("## Response Metadata\n")
        confidence_pct = int(response.overall_confidence * 100)
        parts.append(f"- **Overall Confidence**: {confidence_pct}%")
        parts.append(f"- **Generation Time**: {response.generation_time_ms:.1f}ms")
        parts.append(f"- **Sources Consulted**: {', '.join(response.sources_consulted)}")
        
        if response.response_quality.has_contradictions:
            parts.append("- **Note**: This response contains contradictory information from different sources")
        
        if response.response_quality.degraded_mode:
            parts.append("- **Note**: Generated with limited context (degraded mode)")
        
        return "\n".join(parts)
    
    @staticmethod
    def to_dict_with_citations(response: FinalResponse) -> Dict[str, Any]:
        """
        Convert to dictionary with 3-level citations:
        1. Main answer
        2. Key claims (sections)
        3. Per-claim confidence and source attribution
        
        Args:
            response: FinalResponse to format
            
        Returns:
            Dictionary with detailed citations
        """
        # Build source lookup
        sources_by_id = {s.id: s for s in response.sources}
        
        return {
            "answer": {
                "main": response.answer,
                "confidence": response.overall_confidence,
                "confidence_percentage": f"{int(response.overall_confidence * 100)}%",
            },
            "key_claims": [
                {
                    "claim": section.heading,
                    "details": section.content,
                    "confidence": section.confidence,
                    "confidence_percentage": f"{int(section.confidence * 100)}%",
                    "sources": [
                        {
                            "id": source_id,
                            "title": sources_by_id.get(source_id, {}).get("title", "Unknown"),
                            "type": sources_by_id.get(source_id, {}).get("type", "unknown"),
                            "url": sources_by_id.get(source_id, {}).get("url"),
                        }
                        for source_id in section.sources
                    ]
                }
                for section in response.sections
            ],
            "contradictions": {
                "detected": response.response_quality.has_contradictions,
                "perspectives": [
                    {
                        "viewpoint": p.viewpoint,
                        "confidence": p.confidence,
                        "sources": p.sources,
                    }
                    for p in (response.perspectives or [])
                ]
            } if response.perspectives else None,
            "all_sources": [s.to_dict() for s in response.sources],
            "metadata": {
                "generation_time_ms": response.generation_time_ms,
                "query_id": response.query_id,
                "response_id": response.id,
                "generated_at": response.timestamp.isoformat(),
            }
        }


class CitationFormatter:
    """Formats citations in three levels."""
    
    @staticmethod
    def format_with_inline_citations(response: FinalResponse) -> str:
        """
        Format response with inline citations as [1], [2], etc.
        
        Args:
            response: FinalResponse to format
            
        Returns:
            Formatted text with inline citations
        """
        # Build citation map
        citation_map = {}
        for i, source in enumerate(response.sources, 1):
            citation_map[source.id] = i
        
        result = response.answer + "\n\n"
        
        # Add sections with citations
        for section in response.sections:
            result += f"## {section.heading}\n"
            result += section.content
            
            # Add citations for this section
            if section.sources:
                citations = [f"[{citation_map[sid]}]" for sid in section.sources if sid in citation_map]
                result += f" {' '.join(citations)}\n\n"
        
        # Add source bibliography
        result += "\n## References\n"
        for source in response.sources:
            idx = citation_map[source.id]
            result += f"[{idx}] {source.title}"
            if source.url:
                result += f" - {source.url}"
            result += "\n"
        
        return result
    
    @staticmethod
    def format_with_footnotes(response: FinalResponse) -> str:
        """
        Format response with numbered footnotes.
        
        Args:
            response: FinalResponse to format
            
        Returns:
            Formatted text with footnotes
        """
        footnotes = []
        result = response.answer + "\n\n"
        
        # Process sections
        for section in response.sections:
            result += f"## {section.heading}\n"
            result += section.content
            
            # Add footnote markers
            if section.sources:
                footnote_nums = []
                for source_id in section.sources:
                    source = next((s for s in response.sources if s.id == source_id), None)
                    if source:
                        footnote_num = len(footnotes) + 1
                        footnotes.append(source)
                        footnote_nums.append(str(footnote_num))
                
                if footnote_nums:
                    result += f"^{','.join(footnote_nums)}\n\n"
        
        # Add footnotes
        if footnotes:
            result += "\n---\n\n"
            for i, source in enumerate(footnotes, 1):
                result += f"^{i}: {source.title}"
                if source.url:
                    result += f" ({source.url})"
                result += "\n"
        
        return result


class ContradictionFormatter:
    """Formats contradictions from multiple sources."""
    
    @staticmethod
    def format_contradiction_warning(response: FinalResponse) -> str:
        """
        Format warning about contradictions in response.
        
        Args:
            response: FinalResponse with potential contradictions
            
        Returns:
            Formatted contradiction warning
        """
        if not response.response_quality.has_contradictions:
            return ""
        
        warning = "⚠️ **CONTRADICTORY INFORMATION DETECTED**\n\n"
        
        if response.perspectives:
            warning += "Sources provide conflicting viewpoints:\n\n"
            
            for i, perspective in enumerate(response.perspectives, 1):
                warning += f"**View {i}**: {perspective.viewpoint}\n"
                warning += f"- Confidence: {int(perspective.confidence * 100)}%\n"
                warning += f"- Sources: {', '.join(perspective.sources)}\n\n"
            
            warning += "**Recommendation**: Review all sources directly to form your own conclusion.\n"
        
        return warning
    
    @staticmethod
    def format_source_conflict_report(
        response: FinalResponse,
        filtered_context: Optional[FilteredContext] = None
    ) -> Dict[str, Any]:
        """
        Generate detailed conflict report.
        
        Args:
            response: FinalResponse with contradictions
            filtered_context: Optional FilteredContext with contradiction details
            
        Returns:
            Dictionary with conflict details
        """
        report = {
            "has_contradictions": response.response_quality.has_contradictions,
            "perspectives": [],
            "source_agreement": {},
        }
        
        if response.perspectives:
            for perspective in response.perspectives:
                report["perspectives"].append({
                    "claim": perspective.viewpoint,
                    "confidence": perspective.confidence,
                    "supporting_sources": perspective.sources,
                    "weight": perspective.weight,
                })
        
        # Calculate source agreement
        source_types = {}
        for source in response.sources:
            if source.type not in source_types:
                source_types[source.type] = 0
            source_types[source.type] += 1
        
        report["source_agreement"] = source_types
        
        if filtered_context and filtered_context.contradictions_detected:
            report["contradiction_details"] = [
                {
                    "claim_1": c.claim_1,
                    "claim_1_source": c.claim_1_source,
                    "claim_2": c.claim_2,
                    "claim_2_source": c.claim_2_source,
                    "severity": c.severity,
                }
                for c in filtered_context.contradictions_detected
            ]
        
        return report


def format_response(
    response: FinalResponse,
    format_type: str = "markdown",
    include_citations: bool = True,
) -> str:
    """
    Format a response in the specified format.
    
    Args:
        response: FinalResponse to format
        format_type: Output format ("json", "markdown", "inline_citations", "footnotes")
        include_citations: Whether to include citation information
        
    Returns:
        Formatted response string
    """
    if format_type == "json":
        return ResponseFormatter.to_json(response)
    
    elif format_type == "markdown":
        text = ResponseFormatter.to_markdown(response)
        if response.response_quality.has_contradictions:
            warning = ContradictionFormatter.format_contradiction_warning(response)
            text = warning + "\n" + text
        return text
    
    elif format_type == "inline_citations":
        return CitationFormatter.format_with_inline_citations(response)
    
    elif format_type == "footnotes":
        return CitationFormatter.format_with_footnotes(response)
    
    else:
        logger.warning(f"Unknown format type: {format_type}, using markdown")
        return ResponseFormatter.to_markdown(response)
