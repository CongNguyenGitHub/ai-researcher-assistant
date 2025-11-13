"""
UI module for Context-Aware Research Assistant.

Streamlit components and styling for user interface.
"""

from .components import (
    display_response_card,
    display_confidence_gauge,
    display_source_attribution,
    display_contradiction_warning,
    display_filtering_summary,
    display_section_breakdown,
    display_response_metadata,
    display_retrieval_status,
)

from .styles import (
    apply_custom_styles,
    get_color_by_confidence,
    get_emoji_by_confidence,
    get_source_type_emoji,
    format_confidence_badge,
    format_source_badge,
    create_sidebar_menu,
    render_footer,
)

__all__ = [
    # Components
    "display_response_card",
    "display_confidence_gauge",
    "display_source_attribution",
    "display_contradiction_warning",
    "display_filtering_summary",
    "display_section_breakdown",
    "display_response_metadata",
    "display_retrieval_status",
    
    # Styles
    "apply_custom_styles",
    "get_color_by_confidence",
    "get_emoji_by_confidence",
    "get_source_type_emoji",
    "format_confidence_badge",
    "format_source_badge",
    "create_sidebar_menu",
    "render_footer",
]
