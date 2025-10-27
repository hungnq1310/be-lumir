"""Combined Document Processing Pipeline

Single module handling validation, download, LangChain chunking, embedding, and upload.
Improved with better time measurement and performance monitoring."""

import requests
import time
import uuid
import os
import tempfile
import docx2txt
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from contextlib import contextmanager
from abc import ABC, abstractmethod
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

# LangChain imports
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


@dataclass
class TimingMetrics:
    """Container for detailed timing metrics."""

    total_time: float = 0.0
    download_time: float = 0.0
    loading_time: float = 0.0
    chunking_time: float = 0.0
    embedding_time: float = 0.0
    upload_time: float = 0.0
    validation_time: float = 0.0
    timestamps: Dict[str, float] = field(default_factory=dict)

    def start_timer(self, name: str) -> None:
        """Start timing for a specific operation."""
        self.timestamps[f"{name}_start"] = time.perf_counter()

    def end_timer(self, name: str) -> float:
        """End timing for a specific operation and return duration."""
        start_key = f"{name}_start"
        if start_key not in self.timestamps:
            logger.warning(f"Timer '{name}' was not started")
            return 0.0

        duration = time.perf_counter() - self.timestamps[start_key]
        self.timestamps[f"{name}_duration"] = duration

        # Update specific timing attributes
        if hasattr(self, f"{name}_time"):
            setattr(self, f"{name}_time", duration)

        return duration

    def get_timing_summary(self) -> Dict[str, float]:
        """Get a summary of all timing metrics."""
        return {
            "total_time": self.total_time,
            "download_time": self.download_time,
            "loading_time": self.loading_time,
            "chunking_time": self.chunking_time,
            "embedding_time": self.embedding_time,
            "upload_time": self.upload_time,
            "validation_time": self.validation_time,
        }


@dataclass
class ProcessingResult:
    """Container for processing operation results."""

    success: bool
    documents_processed: int
    total_chunks_created: int
    total_size_bytes: int
    timing_metrics: TimingMetrics = field(default_factory=TimingMetrics)
    errors: List[str] = field(default_factory=list)
    performance_stats: Dict[str, Any] = field(default_factory=dict)


class ProcessingError(Exception):
    """Custom exception for processing errors."""

    pass


@contextmanager
def timer_context(metrics: TimingMetrics, name: str):
    """Context manager for timing operations."""
    metrics.start_timer(name)
    try:
        yield
    finally:
        metrics.end_timer(name)


@contextmanager
def api_session(config: Dict):
    """Context manager for API session."""
    session = requests.Session()

    headers = {"Accept": "*/*", "Content-Type": "application/json"}
    if config.get("api_key"):
        headers["Authorization"] = f"Bearer {config['api_key']}"

    session.headers.update(headers)

    try:
        yield session
    finally:
        session.close()


@contextmanager
def managed_temp_directory():
    """Context manager for temporary directory."""
    temp_dir = os.path.join(
        tempfile.gettempdir(), f"windmill_docs_{uuid.uuid4().hex[:8]}"
    )
    os.makedirs(temp_dir, exist_ok=True)

    try:
        yield temp_dir
    finally:
        # Cleanup temp directory
        try:
            for file in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(temp_dir)
            logger.info(f"Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Error cleaning temp directory: {e}")


# Document Loaders
class DocumentLoader(ABC):
    @abstractmethod
    def load(self, file_path: str) -> List[Any]:
        pass


class PDFDocumentLoader(DocumentLoader):
    def load(self, file_path: str) -> List[Any]:
        return PyPDFLoader(file_path).load()


class DocxDocumentLoader(DocumentLoader):
    def load(self, file_path: str) -> List[Any]:
        text = docx2txt.process(file_path)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(text)
            temp_text_path = f.name

        try:
            return TextLoader(temp_text_path, encoding="utf-8").load()
        finally:
            if os.path.exists(temp_text_path):
                os.remove(temp_text_path)


class TextDocumentLoader(DocumentLoader):
    def load(self, file_path: str) -> List[Any]:
        return TextLoader(file_path, encoding="utf-8").load()


class DocumentLoaderFactory:
    """Factory for creating document loaders."""

    _loaders = {
        "pdf": PDFDocumentLoader,
        "docx": DocxDocumentLoader,
        "txt": TextDocumentLoader,
    }

    @classmethod
    def get_loader(cls, file_type: str) -> DocumentLoader:
        loader_class = cls._loaders.get(file_type.lower())
        if not loader_class:
            raise ValueError(f"Unsupported file type: {file_type}")
        return loader_class()


class DocumentAPI:
    """Unified API client for document operations."""

    def __init__(self, session: requests.Session, config: Dict):
        self.session = session
        self.config = config
        self.timeout = config.get("api_timeout", 30)
        self.max_retries = config.get("max_download_retries", 3)

    def get_document_metadata(self, document_id: str) -> Dict[str, Any]:
        """Get document metadata."""
        try:
            url = f"{self.config['docman_api_base_url'].rstrip('/')}/api/v1/documents/"
            response = self.session.get(
                url, params={"document_id": document_id}, timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json().get("documents", [])
            return data[0] if data else {}

        except requests.RequestException as e:
            raise ProcessingError(f"Failed to get metadata for {document_id}: {e}")

    def download_document(
        self, document_id: str, temp_dir: str, metrics: TimingMetrics
    ) -> tuple[str, Dict[str, Any]]:
        """Download document to temp file."""
        with timer_context(metrics, "download"):
            metadata = self.get_document_metadata(document_id)
            filename = metadata.get("filename", f"document_{document_id}")
            content_type = metadata.get("content_type", "")

            if not content_type or not filename.endswith(f".{content_type}"):
                raise ProcessingError(
                    f"Invalid content type for document {document_id}"
                )

            temp_file_path = os.path.join(temp_dir, f"{document_id}_{filename}")
            url = f"{self.config['docman_api_base_url'].rstrip('/')}/api/v1/documents/{document_id}/download"

            for attempt in range(self.max_retries):
                try:
                    response = self.session.get(url, timeout=self.timeout, stream=True)
                    response.raise_for_status()

                    with open(temp_file_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    file_size = os.path.getsize(temp_file_path)
                    if file_size == 0:
                        raise ProcessingError(
                            f"Empty file downloaded for {document_id}"
                        )

                    print(f"Downloaded {document_id}: {file_size} bytes")
                    return temp_file_path, metadata

                except requests.RequestException as e:
                    if attempt == self.max_retries - 1:
                        raise ProcessingError(f"Download failed for {document_id}: {e}")
                    time.sleep(0.5 * (attempt + 1))  # Reduced sleep time

    def get_text_embedding(self, text: str) -> List[float]:
        """Get embedding for text via Context API."""
        url = f"{self.config['context_api_base_url'].rstrip('/')}/context"
        max_retries = self.config.get("max_chunking_retries", 2)

        for attempt in range(max_retries):
            try:
                response = self.session.post(
                    url,
                    params={"text": text},
                    timeout=self.timeout,
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()

                result = response.json()
                if (
                    not result
                    or not isinstance(result, list)
                    or not result[0].get("emb")
                ):
                    raise ProcessingError("Invalid embedding response")

                return result[0]["emb"]

            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    raise ProcessingError(f"Embedding failed: {e}")
                time.sleep(0.5 * (attempt + 1))  # Reduced sleep time

    def upload_chunks_batch(
        self,
        session_id: str,
        chunks: List[Dict],
        tenant: str,
        batch_size: int,
        metrics: TimingMetrics,
    ) -> Dict:
        """Upload chunks in batches."""
        with timer_context(metrics, "upload"):
            url = f"{self.config['chunk_api_base_url'].rstrip('/')}/api/v1/chunks/session/{session_id}/chunks"
            total_chunks = len(chunks)
            successful_batches = 0
            failed_batches = 0
            total_uploaded = 0
            errors = []

            print(f"Uploading {total_chunks} chunks in batches of {batch_size}")

            for i in range(0, total_chunks, batch_size):
                batch_start = time.perf_counter()
                batch_chunks = chunks[i : i + batch_size]
                batch_number = (i // batch_size) + 1

                try:
                    payload = {"chunks": batch_chunks, "collection_name": tenant}
                    response = self.session.post(
                        url, json=payload, timeout=self.timeout
                    )
                    response.raise_for_status()

                    result = response.json()
                    uploaded = result.get("chunks_processed", len(batch_chunks))
                    total_uploaded += uploaded
                    successful_batches += 1

                    batch_time = time.perf_counter() - batch_start
                    print(
                        f"Batch {batch_number}: {uploaded} chunks uploaded in {batch_time:.2f}s"
                    )

                except requests.RequestException as e:
                    failed_batches += 1
                    error_msg = f"Batch {batch_number} failed: {e}"
                    errors.append(error_msg)
                    print(error_msg)
                    continue

                # Minimal pause between batches
                if i + batch_size < total_chunks:
                    time.sleep(0.001)

            return {
                "success": failed_batches == 0,
                "total_chunks": total_chunks,
                "uploaded_chunks": total_uploaded,
                "successful_batches": successful_batches,
                "failed_batches": failed_batches,
                "errors": errors,
            }


class DocumentPipeline:
    """Main document processing pipeline."""

    def __init__(self, config: Dict):
        self.config = self._validate_config(config)

        # Initialize chunker
        chunk_size = config.get("chunk_size", 500)
        chunk_overlap = config.get("chunk_overlap", 100)
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

    def _validate_config(self, config: Dict) -> Dict:
        """Validate configuration."""
        required_urls = [
            "docman_api_base_url",
            "context_api_base_url",
            "chunk_api_base_url",
        ]

        for url_key in required_urls:
            if not config.get(url_key):
                raise ValueError(f"Missing required configuration: {url_key}")

        # Set defaults
        config.setdefault("api_timeout", 30)
        config.setdefault("max_download_retries", 3)
        config.setdefault("max_chunking_retries", 2)
        config.setdefault("max_upload_retries", 3)

        return config

    def _validate_inputs(
        self, upload_documents: List[str], session_id: str, metrics: TimingMetrics
    ) -> List[str]:
        """Validate input parameters."""
        with timer_context(metrics, "validation"):
            if not session_id or not session_id.strip():
                raise ValueError("Session ID is required")

            if not upload_documents:
                raise ValueError("No documents provided")

            # Clean and deduplicate documents
            clean_docs = list(
                set(doc.strip() for doc in upload_documents if doc and doc.strip())
            )
            if not clean_docs:
                raise ValueError("No valid document IDs found")

            return clean_docs

    def _process_single_document(
        self,
        document_id: str,
        session_id: str,
        api_client: DocumentAPI,
        temp_dir: str,
        metrics: TimingMetrics,
    ) -> tuple[List[Dict], Dict]:
        """Process a single document."""
        doc_start_time = time.perf_counter()

        # Download document
        file_path, metadata = api_client.download_document(
            document_id, temp_dir, metrics
        )
        filename = metadata.get("filename", f"document_{document_id}")
        content_type = metadata.get("content_type", "")

        # Load document with LangChain
        with timer_context(metrics, "loading"):
            loader = DocumentLoaderFactory.get_loader(content_type)
            documents = loader.load(file_path)

            if not documents:
                raise ProcessingError(f"No documents loaded from {filename}")

        # Chunk with LangChain
        with timer_context(metrics, "chunking"):
            chunks = self.splitter.split_documents(documents)
            if not chunks:
                raise ProcessingError(f"No chunks generated for {filename}")

            print(f"Generated {len(chunks)} chunks from {filename}")

        # Get embeddings for chunks with timing
        embedding_start = time.perf_counter()
        chunk_metadata = []

        # Process embeddings in batches for better performance
        batch_size = 10
        for batch_start in range(0, len(chunks), batch_size):
            batch_end = min(batch_start + batch_size, len(chunks))
            batch_chunks = chunks[batch_start:batch_end]

            for i, chunk in enumerate(batch_chunks, batch_start):
                try:
                    embedding = api_client.get_text_embedding(chunk.page_content)

                    chunk_id = str(
                        uuid.uuid5(
                            uuid.NAMESPACE_DNS,
                            f"{document_id}_{i}_{chunk.page_content[:50]}",
                        )
                    )

                    chunk_data = {
                        "chunk_id": chunk_id,
                        "document_id": document_id,
                        "document_title": filename,
                        "chunk_text": chunk.page_content,
                        "vector": embedding,
                        "chunk_index": i,
                        "session_id": session_id,
                        "metadata": {
                            "chunk_length": len(chunk.page_content),
                            "processing_timestamp": time.perf_counter(),  # Use perf_counter for consistency
                            "original_filename": filename,
                            "content_type": content_type,
                            "file_size": metadata.get("file_size", 0),
                            "langchain_metadata": getattr(chunk, "metadata", {}),
                        },
                    }

                    chunk_metadata.append(chunk_data)

                    if (i + 1) % 10 == 0:
                        elapsed = time.perf_counter() - embedding_start
                        rate = (i + 1) / elapsed if elapsed > 0 else 0
                        print(
                            f"Processed {i + 1}/{len(chunks)} chunks (rate: {rate:.2f} chunks/s)"
                        )

                except Exception as e:
                    print(f"Failed to process chunk {i + 1}: {e}")
                    continue

            # Minimal delay between batches
            if batch_end < len(chunks):
                time.sleep(0.001)

        embedding_time = time.perf_counter() - embedding_start
        metrics.embedding_time += embedding_time

        doc_total_time = time.perf_counter() - doc_start_time
        print(f"Document {document_id} processed in {doc_total_time:.2f}s")

        return chunk_metadata, metadata

    def process_documents(
        self,
        upload_documents: List[str],
        session_id: str,
        tenant_name: Optional[str] = None,
        batch_size_insert: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Main processing function."""
        # Initialize timing metrics
        metrics = TimingMetrics()
        pipeline_start = time.perf_counter()

        try:
            # Validate inputs
            clean_documents = self._validate_inputs(
                upload_documents, session_id, metrics
            )
            tenant = tenant_name or "default"
            batch_size = batch_size_insert or 8

            print(
                f"Processing {len(clean_documents)} documents for session {session_id}"
            )

            all_chunks = []
            processed_count = 0
            total_size = 0
            errors = []

            with managed_temp_directory() as temp_dir:
                with api_session(self.config) as session:
                    api_client = DocumentAPI(session, self.config)

                    # Process each document
                    for doc_idx, document_id in enumerate(clean_documents, 1):
                        try:
                            print(
                                f"Processing document {doc_idx}/{len(clean_documents)}: {document_id}"
                            )
                            chunks, metadata = self._process_single_document(
                                document_id, session_id, api_client, temp_dir, metrics
                            )

                            if chunks:
                                all_chunks.extend(chunks)
                                processed_count += 1
                                total_size += metadata.get("file_size", 0)
                                print(
                                    f"✅ Processed {document_id}: {len(chunks)} chunks"
                                )
                            else:
                                errors.append(f"No chunks generated for {document_id}")

                        except Exception as e:
                            error_msg = f"Failed to process {document_id}: {str(e)}"
                            errors.append(error_msg)
                            print(f"❌ {error_msg}")
                            continue

                    # Upload all chunks
                    upload_result = {}
                    if all_chunks:
                        print(f"Uploading {len(all_chunks)} chunks...")
                        upload_result = api_client.upload_chunks_batch(
                            session_id, all_chunks, tenant, batch_size, metrics
                        )

            # Calculate total time
            metrics.total_time = time.perf_counter() - pipeline_start

            # Performance statistics
            performance_stats = {
                "chunks_per_second": len(all_chunks) / metrics.total_time
                if metrics.total_time > 0
                else 0,
                "documents_per_second": processed_count / metrics.total_time
                if metrics.total_time > 0
                else 0,
                "bytes_per_second": total_size / metrics.total_time
                if metrics.total_time > 0
                else 0,
                "average_chunks_per_doc": len(all_chunks) / processed_count
                if processed_count > 0
                else 0,
                "timing_breakdown": metrics.get_timing_summary(),
            }

            result = {
                "success": processed_count > 0 and upload_result.get("success", False),
                "documents_processed": processed_count,
                "total_chunks_created": len(all_chunks),
                "uploaded_chunks": upload_result.get("uploaded_chunks", 0),
                "total_size_bytes": total_size,
                "session_id": session_id,
                "tenant_name": tenant,
                "errors": errors + upload_result.get("errors", []),
                "timing_metrics": metrics.get_timing_summary(),
                "performance_stats": performance_stats,
            }

            print(f"\n🎯 Pipeline Summary:")
            print(f"   Documents: {processed_count}/{len(clean_documents)}")
            print(
                f"   Chunks: {len(all_chunks)} created, {upload_result.get('uploaded_chunks', 0)} uploaded"
            )
            print(f"   Total time: {metrics.total_time:.2f}s")
            print(
                f"   Performance: {performance_stats['chunks_per_second']:.2f} chunks/s"
            )
            print(f"   Timing breakdown: {metrics.get_timing_summary()}")

            return result

        except Exception as e:
            metrics.total_time = time.perf_counter() - pipeline_start
            logger.error(f"Pipeline failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timing_metrics": metrics.get_timing_summary(),
            }


def main(
    upload_documents: List[str],
    session_id: str,
    config: Dict[str, Any],
    tenant_name: Optional[str] = None,
    batch_size_insert: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Main entry point for document processing pipeline.

    Args:
        upload_documents: List of document IDs to process
        session_id: Session identifier
        config: Configuration dictionary
        tenant_name: Tenant identifier
        batch_size_insert: Batch size for uploads

    Returns:
        Processing results with detailed timing metrics
    """
    pipeline = DocumentPipeline(config)
    return pipeline.process_documents(
        upload_documents, session_id, tenant_name, batch_size_insert
    )
