"""Upload Search Service - Optimized with Connection Pooling"""

import requests
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

@contextmanager
def search_session(config: Dict):
    """Optimized session with connection pooling"""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=2,
        backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"]
    )
    
    adapter = HTTPAdapter(
        pool_connections=10,
        pool_maxsize=20,
        max_retries=retry_strategy,
        pool_block=False
    )
    
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    headers = {
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive"
    }
    
    if config.get("api_key"):
        headers["Authorization"] = f"Bearer {config['api_key']}"
    
    session.headers.update(headers)
    
    try:
        yield session
    finally:
        session.close()

class PostUploadSearcher:
    def __init__(self, session: requests.Session, config: Dict):
        self.session = session
        self.config = config
        self.timeout = (
            config.get("api_connect_timeout", 3),
            config.get("api_timeout", 20)
        )

    def generate_embedding(self, text: str) -> np.ndarray:
        try:
            url = f"{self.config['embedding_api_base_url']}/query"
            payload = {"text": text, "model_name": "retrieve_query"}

            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            if not data:
                raise Exception("Empty embedding response")

            embedding = data[0]["emb"]
            return np.array(embedding, dtype=np.float32)

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    def search_uploaded_content(
        self,
        query_vector: List[float],
        session_id: str,
        collection_name: Optional[str] = None,
    ) -> List[Dict]:
        try:
            url = f"{self.config['search_api_base_url']}/api/v1/chunks/session/{session_id}/search"

            payload = {
                "query_vector": query_vector,
                "limit": 10,
                "filters": {"source": "upload"},
            }

            if collection_name:
                payload["collection_name"] = collection_name

            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            results = []

            for result in data.get("results", []):
                formatted_result = {
                    "id": result.get("chunk_id"),
                    "score": result.get("similarity_score", 0.0),
                    "payload": {
                        "chunk_id": result.get("chunk_id"),
                        "document_id": result.get("document_id"),
                        "doc_title": result.get("document_title"),
                        "chunk_content": result.get("chunk_text"),
                        "source": "upload",
                        **result.get("metadata", {}),
                    },
                }
                results.append(formatted_result)

            return results

        except Exception as e:
            logger.error(f"Upload search failed: {e}")
            return []

def main(
    query: str,
    config: Dict,
    session_id: str,
    tenant: Optional[str] = None,
    processing_result: Optional[Dict] = None,
) -> List[Dict]:
    """Search in uploaded documents with optimized connection."""
    
    try:
        if not processing_result:
            logger.warning("Document processing failed, skipping upload search")
            return []

        with search_session(config) as session:
            searcher = PostUploadSearcher(session, config)

            query_embedding = searcher.generate_embedding(query)
            if not isinstance(query_embedding, list):
                query_embedding = query_embedding.tolist()

            results = searcher.search_uploaded_content(
                query_vector=query_embedding,
                session_id=session_id,
                collection_name=tenant,
            )

            logger.info(f"Found {len(results)} upload results")
            return results

    except Exception as e:
        logger.error(f"Upload search service failed: {e}")
        return []
