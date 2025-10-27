"""Reranking Service - Optimized with Connection Pooling"""

import logging
import requests
from typing import List, Dict, Any
from contextlib import contextmanager
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class RerankingError(Exception):
    pass

@contextmanager
def reranking_session(config: Dict):
    """Optimized session with connection pooling"""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=2,
        backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"]
    )
    
    adapter = HTTPAdapter(
        pool_connections=5,
        pool_maxsize=10,
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

class ResultReranker:
    def __init__(self, session: requests.Session, config: Dict):
        self.session = session
        self.base_url = config["api_base_url"].rstrip("/")
        self.timeout = (
            config.get("api_connect_timeout", 3),
            config.get("api_timeout", 20)
        )
    
    def rerank_results(self, query: str, search_results: list) -> list:
        if not search_results:
            return search_results
        
        try:
            contexts = self._extract_contexts(search_results)
            if not contexts:
                logger.warning("No valid contexts found for reranking")
                return search_results
            
            scores = self._call_reranking_api(query, contexts)
            if not scores or len(scores) != len(search_results):
                logger.warning("Invalid reranking response, using original order")
                return search_results
            
            reranked_results = self._apply_reranking_scores(search_results, scores)
            return reranked_results
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return search_results
    
    def _extract_contexts(self, search_results: list) -> list:
        contexts = []
        for result in search_results:
            context_text = ""
            if hasattr(result, "payload") and "chunk_content" in result.payload:
                context_text = result.payload["chunk_content"]
            elif isinstance(result, dict) and "payload" in result:
                context_text = result["payload"].get("chunk_content", "")
            contexts.append(context_text)
        return contexts
    
    def _call_reranking_api(self, query: str, contexts: list) -> list:
        url = f"{self.base_url}/rerank"
        payload = {"query": query, "contexts": contexts}
        
        response = self.session.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        
        rerank_data = response.json()
        return rerank_data.get("scores", [])
    
    def _apply_reranking_scores(self, search_results: list, scores: list) -> list:
        reranked_results = []
        
        for i, (result, score) in enumerate(zip(search_results, scores)):
            if isinstance(result, dict):
                result_copy = result.copy()
                result_copy["rerank_score"] = score
            else:
                result_copy = {
                    "id": getattr(result, "id", f"result_{i}"),
                    "score": getattr(result, "score", 0.0),
                    "payload": getattr(result, "payload", {}),
                    "rerank_score": score,
                }
            reranked_results.append(result_copy)
        
        reranked_results.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        return reranked_results

def main(query: str, search_results: list, config: Dict, enable_rerank: bool = False) -> list:
    """Main reranking function with optimized connection."""
    
    try:
        if not enable_rerank:
            logger.info("Reranking disabled, returning original results")
            return search_results
        
        if not search_results:
            logger.info("No results to rerank")
            return search_results
        
        with reranking_session(config) as session:
            reranker = ResultReranker(session, config)
            reranked_results = reranker.rerank_results(query, search_results)
            
            logger.info(f"Reranked {len(reranked_results)} results")
            return reranked_results
            
    except Exception as e:
        logger.error(f"Reranking service failed: {e}")
        return search_results
