"""Context Service"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ContextItem:
    id: str
    score: float
    text: str
    metadata: Dict[str, Any]
    source: str

class ContextProcessor:
    def __init__(self, max_contexts: int = 5, min_score_threshold: float = 0.0):
        self.max_contexts = max_contexts
        self.min_score_threshold = min_score_threshold
    
    def process_search_results(self, search_results: list) -> list:
        contexts = []
        for result in search_results:
            try:
                context_item = self._extract_context_item(result)
                if context_item and self._validate_context_item(context_item):
                    contexts.append(context_item)
            except Exception as e:
                logger.warning(f"Failed to process search result: {e}")
                continue
        return contexts
    
    def _extract_context_item(self, result: Dict) -> Optional[ContextItem]:
        if not isinstance(result, dict):
            return None
        
        context_id = result.get("id", "unknown")
        score = result.get("score", 0.0)
        
        payload = result.get("payload", {})
        text = (
            payload.get("chunk_content") or 
            payload.get("text") or 
            payload.get("chunk_text") or 
            ""
        )
        
        if not text.strip():
            return None
        
        source = payload.get("source", "search")
        
        return ContextItem(
            id=context_id,
            score=score,
            text=text.strip(),
            metadata=payload,
            source=source,
        )
    
    def _validate_context_item(self, context_item: ContextItem) -> bool:
        if context_item.score < self.min_score_threshold:
            return False
        if len(context_item.text) < 10:
            return False
        return True
    
    def select_top_contexts(self, contexts: list) -> list:
        if not contexts:
            return []
        
        sorted_contexts = sorted(
            contexts, key=lambda x: (x.score, len(x.text)), reverse=True
        )
        
        selected = sorted_contexts[:self.max_contexts]
        return selected
    
    def format_contexts_for_llm(self, contexts: list) -> str:
        if not contexts:
            return ""
        
        formatted_parts = ["=== REFERENCE INFORMATION ==="]
        
        for i, context in enumerate(contexts, 1):
            doc_identifier = self._extract_document_identifier(context)
            formatted_parts.extend([
                f"\nContext {i} (from {doc_identifier}):",
                context.text
            ])
        
        formatted_parts.append("\n=== END REFERENCE INFORMATION ===")
        return "\n".join(formatted_parts)
    
    def _extract_document_identifier(self, context: ContextItem) -> str:
        metadata = context.metadata
        identifier = (
            metadata.get("filename") or
            metadata.get("doc_title") or
            metadata.get("document_title") or
            metadata.get("document_name") or
            f"Document {context.id[:8]}"
        )
        return str(identifier)

def main(search_results: list, upload_mode: bool) -> Tuple[list, str]:
    """Main context processing function."""
    
    try:
        max_contexts = 7 if upload_mode else 5
        processor = ContextProcessor(max_contexts=max_contexts)
        
        contexts = processor.process_search_results(search_results)
        selected_contexts = processor.select_top_contexts(contexts)
        formatted_context = processor.format_contexts_for_llm(selected_contexts)
        
        context_dicts = []
        for context in selected_contexts:
            context_dict = {
                "id": context.id,
                "score": context.score,
                "payload": {
                    "text": context.text,
                    "source": context.source,
                    **context.metadata,
                },
            }
            context_dicts.append(context_dict)
        
        logger.info(f"Processed {len(context_dicts)} contexts")
        return context_dicts, formatted_context
        
    except Exception as e:
        logger.error(f"Context service failed: {e}")
        return [], ""
