"""Search Service - Optimized with Connection Pooling & Performance Monitoring"""

import time
import numpy as np
import requests
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class APISearchError(Exception):
    pass


@contextmanager
def api_session(config: Dict):
    """Optimized session with connection pooling and retry strategy"""
    session = requests.Session()

    # Connection pooling configuration
    retry_strategy = Retry(
        total=2,
        backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST", "GET"],
    )

    adapter = HTTPAdapter(
        pool_connections=10,
        pool_maxsize=20,
        max_retries=retry_strategy,
        pool_block=False,
    )

    session.mount("http://", adapter)
    session.mount("https://", adapter)

    headers = {
        "Content-Type": "application/json",
        "Connection": "keep-alive",
    }

    if config.get("api_key"):
        headers["Authorization"] = f"Bearer {config['api_key']}"

    session.headers.update(headers)

    try:
        yield session
    finally:
        session.close()


def generate_embedding(
    session: requests.Session, text: str, config: Dict
) -> Tuple[np.ndarray, float]:
    """
    Generate embedding for query text with performance tracking

    Returns:
        Tuple of (embedding array, execution time in seconds)
    """
    start_time = time.perf_counter()

    try:
        base_url = config["embedding_api_base_url"].rstrip("/")
        timeout = (
            config.get("api_connect_timeout", 3),
            config.get("api_timeout", 20),
        )

        url = f"{base_url}/query"
        payload = {"text": text, "model_name": "retrieve_query"}

        # Track API call time
        api_start = time.perf_counter()
        response = session.post(url, json=payload, timeout=timeout)
        api_time = time.perf_counter() - api_start

        response.raise_for_status()

        data = response.json()
        if not data:
            raise APISearchError("Empty embedding response from API")

        embedding = data[0]["emb"]
        result = np.array(embedding, dtype=np.float32)

        total_time = time.perf_counter() - start_time

        print(
            f"⚡ Embedding generated: "
            f"API={api_time * 1000:.2f}ms, "
            f"Total={total_time * 1000:.2f}ms"
        )

        return result, total_time

    except requests.RequestException as e:
        total_time = time.perf_counter() - start_time
        print(f"❌ Embedding failed after {total_time * 1000:.2f}ms: {e}")
        raise APISearchError(f"Embedding generation failed: {e}")


def perform_semantic_search(
    session: requests.Session,
    query_vector: list,
    session_id: str,
    config: Dict,
    limit: int = 10,
    collection_name: Optional[str] = None,
    filters: Optional[Dict] = None,
) -> Tuple[list, float]:
    """
    Perform semantic search with performance tracking

    Returns:
        Tuple of (search results, execution time in seconds)
    """
    start_time = time.perf_counter()

    try:
        base_url = config["search_api_base_url"].rstrip("/")
        timeout = (
            config.get("api_connect_timeout", 3),
            config.get("api_timeout", 20),
        )

        url = f"{base_url}/api/v1/chunks/session/search"
        payload = {
            "query_vector": query_vector,
            "limit": limit,
            "filters": filters or {},
        }

        if collection_name:
            payload["collection_name"] = collection_name

        # Track API call time
        api_start = time.perf_counter()
        response = session.post(url, json=payload, timeout=timeout)
        api_time = time.perf_counter() - api_start

        response.raise_for_status()

        # Track JSON parsing time
        parse_start = time.perf_counter()
        api_response = response.json()
        parse_time = time.perf_counter() - parse_start

        results = api_response.get("results", [])

        # Track formatting time
        format_start = time.perf_counter()
        formatted_results = format_search_results(results)
        format_time = time.perf_counter() - format_start

        total_time = time.perf_counter() - start_time

        print(
            f"🔍 Search completed: "
            f"API={api_time * 1000:.2f}ms, "
            f"Parse={parse_time * 1000:.2f}ms, "
            f"Format={format_time * 1000:.2f}ms, "
            f"Total={total_time * 1000:.2f}ms, "
            f"Results={len(formatted_results)}"
        )

        return formatted_results, total_time

    except requests.RequestException as e:
        total_time = time.perf_counter() - start_time
        print(f"❌ Search failed after {total_time * 1000:.2f}ms: {e}")
        raise APISearchError(f"Search operation failed: {e}")


def format_search_results(results: list) -> list:
    """Format raw search results into standardized structure"""
    formatted_results = []

    for result in results:
        formatted_result = {
            "id": result.get("chunk_id"),
            "score": result.get("similarity_score", 0.0),
            "payload": {
                "chunk_id": result.get("chunk_id"),
                "document_id": result.get("document_id"),
                "doc_title": result.get("document_title"),
                "chunk_content": result.get("chunk_text"),
                "source": result.get("source", "search"),
                **result.get("metadata", {}),
            },
        }
        formatted_results.append(formatted_result)

    return formatted_results


def main(
    query: str, config: Dict, session_id: str, tenant: Optional[str] = "beq"
) -> list:
    """
    Main search function with comprehensive performance monitoring

    Returns:
        List of formatted search results
    """
    workflow_start = time.perf_counter()

    print("=" * 80)
    print(f"🚀 Starting Search Workflow")
    print(f"   📝 Query: {query[:100]}...")
    print(f"   👤 Session: {session_id}")
    print(f"   🏢 Tenant: {tenant}")
    print("=" * 80)

    try:
        # Step 1: Create optimized session
        session_start = time.perf_counter()
        with api_session(config) as session:
            session_time = time.perf_counter() - session_start
            print(f"✅ Session created: {session_time * 1000:.2f}ms")

            # Step 2: Generate embedding
            print("🔄 Step 1/3: Generating query embedding...")
            query_embedding, embed_time = generate_embedding(session, query, config)

            # Convert to list if needed
            conversion_start = time.perf_counter()
            if not isinstance(query_embedding, list):
                query_embedding = query_embedding.tolist()
            conversion_time = time.perf_counter() - conversion_start

            if conversion_time > 0.001:  # Log only if > 1ms
                print(f"   🔄 Array conversion: {conversion_time * 1000:.2f}ms")

            # Step 3: Perform search
            print("🔄 Step 2/3: Performing semantic search...")
            results, search_time = perform_semantic_search(
                session=session,
                query_vector=query_embedding,
                session_id=session_id,
                limit=config.get("search_limit", 5),
                collection_name=tenant,
                config=config,
            )

            # Calculate total workflow time
            total_workflow_time = time.perf_counter() - workflow_start

            # Performance summary
            print("=" * 80)
            print(f"✅ Search Workflow Completed")
            print(f"📊 Performance Breakdown:")
            print(f"   ├─ Session Setup:    {session_time * 1000:>8.2f}ms")
            print(
                f"   ├─ Embedding:        {embed_time * 1000:>8.2f}ms ({embed_time / total_workflow_time * 100:.1f}%)"
            )
            print(
                f"   ├─ Search:           {search_time * 1000:>8.2f}ms ({search_time / total_workflow_time * 100:.1f}%)"
            )
            print(f"   └─ Total:            {total_workflow_time * 1000:>8.2f}ms")
            print(f"📈 Results: {len(results)} chunks found")
            print("=" * 80)

            return results

    except APISearchError:
        total_time = time.perf_counter() - workflow_start
        print(f"❌ Search workflow failed after {total_time * 1000:.2f}ms")
        raise
    except Exception as e:
        total_time = time.perf_counter() - workflow_start
        print(f"❌ Unexpected error after {total_time * 1000:.2f}ms: {e}")
        return []
