"""
Streamlit page for document processing and management
Handles document upload, parsing, embedding, and vector database indexing
"""

import streamlit as st
import logging
from pathlib import Path
from typing import Optional, List
import time

from src.config import Config
from src.data_ingestion import DataIngestionPipeline

logger = logging.getLogger(__name__)


def initialize_session_state():
    """Initialize Streamlit session state variables"""
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []
    if "processing_results" not in st.session_state:
        st.session_state.processing_results = []
    if "pipeline" not in st.session_state:
        st.session_state.pipeline = None
    if "collection_stats" not in st.session_state:
        st.session_state.collection_stats = {}


def get_pipeline() -> DataIngestionPipeline:
    """Get or create data ingestion pipeline"""
    if st.session_state.pipeline is None:
        config = Config.from_env()

        st.session_state.pipeline = DataIngestionPipeline(
            tensorlake_api_key=config.tensorlake.api_key,
            tensorlake_base_url=config.tensorlake.base_url,
            gemini_api_key=config.gemini.api_key,
            gemini_model=config.gemini.embedding_model,
            milvus_host=config.milvus.host,
            milvus_port=config.milvus.port,
            milvus_user=config.milvus.user,
            milvus_password=config.milvus.password,
            collection_name=config.milvus.collection_name,
        )

    return st.session_state.pipeline


def save_uploaded_file(uploaded_file) -> str:
    """
    Save uploaded file to temporary directory

    Args:
        uploaded_file: Streamlit uploaded file object

    Returns:
        Path to saved file
    """
    upload_dir = Path("temp_uploads")
    upload_dir.mkdir(exist_ok=True)

    file_path = upload_dir / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return str(file_path)


def process_file(file_path: str, pipeline: DataIngestionPipeline):
    """
    Process a single file through the ingestion pipeline

    Args:
        file_path: Path to file to process
        pipeline: DataIngestionPipeline instance
    """
    result = pipeline.process_document(file_path)
    st.session_state.processing_results.append(result)

    # Update collection stats
    st.session_state.collection_stats = pipeline.get_collection_stats()

    return result


def main():
    """Main Streamlit app for document processing"""

    st.set_page_config(
        page_title="Document Processing",
        page_icon="📄",
        layout="wide",
    )

    st.title("📄 Document Processing")
    st.markdown(
        "Upload and process documents to build your knowledge base for research queries."
    )

    # Initialize session state
    initialize_session_state()

    # Create two columns: upload on left, status on right
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Upload Documents")

        uploaded_files = st.file_uploader(
            "Drag and drop or select documents",
            type=["pdf", "docx", "txt", "md"],
            accept_multiple_files=True,
        )

        if uploaded_files:
            st.info(f"📦 {len(uploaded_files)} file(s) selected")

            if st.button("🚀 Process Documents", key="process_btn", use_container_width=True):
                progress_bar = st.progress(0)
                status_container = st.container()

                pipeline = get_pipeline()
                total_files = len(uploaded_files)

                with status_container:
                    for idx, uploaded_file in enumerate(uploaded_files):
                        # Save file
                        file_path = save_uploaded_file(uploaded_file)

                        # Process file
                        with st.spinner(f"Processing {uploaded_file.name}..."):
                            result = process_file(file_path, pipeline)

                            # Update progress
                            progress = (idx + 1) / total_files
                            progress_bar.progress(progress)

                            # Show result
                            if result["status"] == "success":
                                st.success(
                                    f"✓ {uploaded_file.name}: "
                                    f"{result['chunks_parsed']} chunks, "
                                    f"{result['vectors_inserted']} vectors"
                                )
                            else:
                                st.error(
                                    f"✗ {uploaded_file.name}: {result.get('error', 'Unknown error')}"
                                )

                st.success("✅ Processing complete!")

    with col2:
        st.subheader("Knowledge Base Status")

        # Get pipeline for stats
        try:
            pipeline = get_pipeline()
            stats = pipeline.get_collection_stats()

            if stats:
                st.metric(
                    "Documents Indexed",
                    stats.get("num_rows", 0),
                    help="Total number of chunks indexed in the vector database",
                )

                with st.expander("Collection Details", expanded=False):
                    st.json(
                        {
                            "collection": stats.get("name", "N/A"),
                            "total_vectors": stats.get("num_rows", 0),
                            "vector_dimension": 768,
                        }
                    )
            else:
                st.info("No documents processed yet")

        except Exception as e:
            st.warning(f"Could not connect to knowledge base: {str(e)}")
            st.markdown(
                """
                Make sure Milvus is running:
                ```bash
                docker run -d -p 19530:19530 milvusdb/milvus:latest
                ```
                """
            )

        # Recent processing results
        if st.session_state.processing_results:
            st.subheader("Recent Processing")

            results_df_data = []
            for result in st.session_state.processing_results[-5:]:  # Last 5
                results_df_data.append(
                    {
                        "File": result.get("filename", "Unknown"),
                        "Status": result.get("status", "Unknown"),
                        "Chunks": result.get("chunks_parsed", 0),
                        "Vectors": result.get("vectors_inserted", 0),
                    }
                )

            if results_df_data:
                st.dataframe(results_df_data, use_container_width=True)

    # Supported formats info
    st.divider()
    st.subheader("📋 Supported Formats")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("**PDF**\nPortable Document Format")
    with col2:
        st.markdown("**DOCX**\nMicrosoft Word Documents")
    with col3:
        st.markdown("**TXT**\nPlain Text Files")
    with col4:
        st.markdown("**MD**\nMarkdown Files")

    # Processing pipeline info
    st.divider()
    st.subheader("⚙️ Processing Pipeline")

    st.markdown(
        """
    1. **Parse** - Extract text and structure from documents using TensorLake
    2. **Chunk** - Split documents into overlapping semantic chunks (512 tokens, 64 token overlap)
    3. **Embed** - Generate 768-dimensional embeddings using Gemini Text Embeddings
    4. **Index** - Load vectors into Milvus for semantic search
    """
    )


if __name__ == "__main__":
    main()
