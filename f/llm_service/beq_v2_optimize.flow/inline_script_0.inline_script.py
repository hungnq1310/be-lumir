"""Configuration validation and setup module - Optimized"""

import os
import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
import wmill

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    """API-based system configuration with optimized timeouts."""

    rag_api_base_url: str
    docman_api_base_url: str
    api_key: Optional[str] = None
    api_timeout: int = 20
    api_connect_timeout: int = 3
    chunk_size: int = 500
    chunk_overlap: int = 100
    search_limit: int = 10
    llm_model: str = "gpt-4.1-nano-2025-04-14"
    temperature: float = 0.6
    max_tokens: int = 5000
    top_p: float = 0.6

    def validate(self) -> None:
        required = ["rag_api_base_url", "docman_api_base_url"]
        for field in required:
            value = getattr(self, field)
            if not value:
                raise ValueError(f"Missing required config: {field}")
            if not value.startswith(("http://", "https://")):
                raise ValueError(f"Invalid URL format for {field}: {value}")

    def derive_service_urls(self) -> Dict[str, str]:
        rag_base = self.rag_api_base_url.rstrip("/")
        docman_base = self.docman_api_base_url.rstrip("/")

        return {
            "api_base_url": rag_base,
            "rag_api_base_url": rag_base,
            "docman_api_base_url": docman_base,
            "document_api_base_url": docman_base,
            "chunk_api_base_url": docman_base,
            "search_api_base_url": docman_base,
            "embedding_api_base_url": rag_base,
            "context_api_base_url": rag_base,
        }


def main(raw_configs: Dict[str, Any]) -> Dict[str, Any]:
    """Main configuration validation function."""

    try:
        api_config_data = raw_configs

        config = APIConfig(
            rag_api_base_url=api_config_data.get("rag_url", ""),
            docman_api_base_url=api_config_data.get("docman_url", ""),
            api_key=api_config_data.get("api_key"),
            api_timeout=api_config_data.get("timeout", 20),
            api_connect_timeout=api_config_data.get("connect_timeout", 3),
        )

        result_config = asdict(config)
        result_config.update(config.derive_service_urls())

        logger.info("Configuration validation completed successfully")
        return result_config

    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise
