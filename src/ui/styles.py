"""
Styling and theme configuration for Streamlit application.

Provides CSS and configuration for consistent UI appearance.
"""

import streamlit as st


def apply_custom_styles():
    """Apply custom CSS styles to the Streamlit app."""
    st.markdown(
        """
        <style>
        /* Main container styling */
        .main {
            padding-top: 1rem;
        }
        
        /* Header styling */
        h1, h2, h3 {
            color: #1f77b4;
            font-weight: 600;
        }
        
        /* Success/warning/error boxes */
        .stSuccess {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 5px;
            padding: 1rem;
        }
        
        .stWarning {
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 5px;
            padding: 1rem;
        }
        
        .stError {
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 5px;
            padding: 1rem;
        }
        
        /* Cards styling */
        .card {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
        
        /* Citation styling */
        .citation {
            color: #666;
            font-size: 0.9em;
            border-left: 3px solid #1f77b4;
            padding-left: 0.5rem;
            margin: 0.5rem 0;
        }
        
        /* Metrics styling */
        .metric-value {
            font-size: 2rem;
            font-weight: bold;
            color: #1f77b4;
        }
        
        /* Table styling */
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 1rem 0;
        }
        
        th {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 0.75rem;
            text-align: left;
            font-weight: 600;
        }
        
        td {
            border: 1px solid #dee2e6;
            padding: 0.75rem;
        }
        
        tr:hover {
            background-color: #f8f9fa;
        }
        
        /* Expander styling */
        .streamlit-expanderHeader {
            font-weight: 500;
        }
        
        /* Source box styling */
        .source-box {
            background-color: #f0f2f6;
            border-radius: 5px;
            padding: 1rem;
            margin: 0.5rem 0;
            border-left: 4px solid #1f77b4;
        }
        
        /* Confidence indicator */
        .confidence-high {
            color: #28a745;
            font-weight: bold;
        }
        
        .confidence-medium {
            color: #ffc107;
            font-weight: bold;
        }
        
        .confidence-low {
            color: #dc3545;
            font-weight: bold;
        }
        
        /* Response text styling */
        .response-answer {
            font-size: 1.1em;
            line-height: 1.6;
            margin: 1rem 0;
        }
        
        .response-section {
            background-color: #f8f9fa;
            border-left: 4px solid #1f77b4;
            padding: 1rem;
            margin: 0.5rem 0;
            border-radius: 4px;
        }
        
        /* Button styling */
        .stButton > button {
            width: 100%;
            border-radius: 5px;
            font-weight: 500;
            height: 2.5rem;
        }
        
        /* Input styling */
        .stTextArea > textarea {
            border-radius: 5px;
        }
        
        .stSelectbox, .stMultiSelect {
            border-radius: 5px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_color_by_confidence(confidence: float) -> str:
    """
    Get color based on confidence level.
    
    Args:
        confidence: Confidence value (0-1)
        
    Returns:
        Hex color code
    """
    if confidence >= 0.8:
        return "#28a745"  # Green
    elif confidence >= 0.6:
        return "#0066cc"  # Blue
    elif confidence >= 0.4:
        return "#ffc107"  # Orange
    else:
        return "#dc3545"  # Red


def get_emoji_by_confidence(confidence: float) -> str:
    """
    Get emoji based on confidence level.
    
    Args:
        confidence: Confidence value (0-1)
        
    Returns:
        Emoji string
    """
    if confidence >= 0.8:
        return "✅"
    elif confidence >= 0.6:
        return "✓"
    elif confidence >= 0.4:
        return "⚠️"
    else:
        return "❌"


def get_source_type_emoji(source_type: str) -> str:
    """
    Get emoji for source type.
    
    Args:
        source_type: Type of source (rag, web, arxiv, memory)
        
    Returns:
        Emoji string
    """
    emojis = {
        "rag": "📄",
        "web": "🌐",
        "arxiv": "📚",
        "memory": "💭",
    }
    return emojis.get(source_type.lower(), "📌")


def format_confidence_badge(confidence: float) -> str:
    """
    Format confidence as an HTML badge.
    
    Args:
        confidence: Confidence value (0-1)
        
    Returns:
        HTML badge string
    """
    percentage = int(confidence * 100)
    color = get_color_by_confidence(confidence)
    emoji = get_emoji_by_confidence(confidence)
    
    return f"""
    <span style='background-color: {color}20; border: 1px solid {color}; 
                 border-radius: 4px; padding: 4px 8px; margin: 2px;'>
        {emoji} {percentage}%
    </span>
    """


def format_source_badge(source_type: str, relevance: float) -> str:
    """
    Format source as an HTML badge.
    
    Args:
        source_type: Type of source
        relevance: Relevance score (0-1)
        
    Returns:
        HTML badge string
    """
    emoji = get_source_type_emoji(source_type)
    color = get_color_by_confidence(relevance)
    
    return f"""
    <span style='background-color: {color}20; border: 1px solid {color};
                 border-radius: 4px; padding: 4px 8px; margin: 2px;'>
        {emoji} {source_type.upper()}
    </span>
    """


def create_sidebar_menu() -> str:
    """
    Create sidebar menu structure.
    
    Returns:
        Selected menu item
    """
    st.sidebar.markdown("## Navigation")
    menu = st.sidebar.radio(
        "Select Page",
        ["Home", "Research", "Documents", "Memory", "Settings"],
        label_visibility="collapsed",
    )
    return menu


def render_footer():
    """Render application footer."""
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.caption("📊 Context-Aware Research Assistant v0.1")
    
    with col2:
        st.caption("🔐 All data processed locally")
    
    with col3:
        st.caption("📝 [View Documentation](https://github.com)")


# Apply styles when imported
apply_custom_styles()
