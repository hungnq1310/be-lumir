"""LLM Service - Optimized with Connection Pooling & Timeout"""

import logging
import requests
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class WindmillStatusManager:
    """Manages status updates to the middleware following job status-based flow"""

    def __init__(
        self,
        callback_base: str,
        correlation_id: str,
        workspace_path: str = "finops",
        session_id: str = "",
    ):
        self.callback_base = callback_base.rstrip("/")
        self.correlation_id = correlation_id
        self.workspace_path = workspace_path
        self.session_id = session_id

        # Optimized session with connection pooling
        self.session = requests.Session()

        retry_strategy = Retry(
            total=2,
            backoff_factor=0.2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
        )

        adapter = HTTPAdapter(
            pool_connections=5,
            pool_maxsize=10,
            max_retries=retry_strategy,
            pool_block=False,
        )

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Connection": "keep-alive",
            }
        )

        logger.info(f"🏗️ WindmillStatusManager initialized:")
        logger.info(f"   📍 Callback Base: {self.callback_base}")
        logger.info(f"   🔗 Correlation ID: {self.correlation_id}")
        logger.info(f"   🏢 Workspace: {self.workspace_path}")
        logger.info(f"   👤 Session: {self.session_id}")

    def notify_step_completion(self, step_name: str = "processing") -> bool:
        """Notify middleware of step completion with optimized timeout"""
        try:
            callback_url = f"{self.callback_base}/windmill/update"

            payload = {
                "session_id": self.session_id,
                "correlation_id": self.correlation_id,
                "workspace_path": self.workspace_path,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "step_completed": step_name,
            }

            logger.info(f"📤 Sending status update for step '{step_name}'")

            # Optimized timeout: (connect_timeout, read_timeout)
            response = self.session.post(callback_url, json=payload, timeout=(2, 10))
            response.raise_for_status()

            response_data = response.json()
            logger.info(f"✅ Status update acknowledged: {response_data}")

            return response_data.get("acknowledged", False)

        except requests.exceptions.Timeout as e:
            logger.error(f"⏰ Timeout sending status update: {e}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"🌐 HTTP error sending status update: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error sending status update: {e}")
            return False

    def __del__(self):
        """Cleanup session on deletion"""
        if hasattr(self, "session"):
            self.session.close()


@dataclass
class LLMConfiguration:
    """LLM configuration settings"""

    model: str = "moonshotai/kimi-k2-instruct-0905"
    temperature: float = 0.6
    max_tokens: int = 5000
    top_p: float = 0.6


class LanguageDetector:
    """Detects language of input text"""

    VIETNAMESE_CHARS = (
        "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
    )
    VIETNAMESE_WORDS = {
        "là",
        "có",
        "không",
        "thế",
        "nào",
        "ở",
        "đâu",
        "gì",
        "như",
        "về",
        "của",
        "một",
        "này",
        "đó",
        "cho",
        "với",
        "được",
        "sẽ",
        "đã",
        "khi",
        "nếu",
        "để",
        "và",
        "hay",
        "hoặc",
        "nhưng",
        "vì",
        "do",
        "theo",
        "từ",
        "trong",
        "trên",
        "dưới",
        "giữa",
        "sau",
        "trước",
    }

    @classmethod
    def detect_language(cls, text: str) -> str:
        """Detect if text is Vietnamese or English"""
        text_lower = text.lower()
        if any(char in text_lower for char in cls.VIETNAMESE_CHARS):
            return "vietnamese"
        text_words = set(text_lower.split())
        if text_words.intersection(cls.VIETNAMESE_WORDS):
            return "vietnamese"
        return "english"


class PromptManager:
    """Manages prompt construction for different languages"""

    SYSTEM_PROMPT = """You are a professional Q&A assistant designed to provide accurate, concise answers based on the provided reference materials. Your primary role is to help users find specific information quickly and efficiently.

## CRITICAL LANGUAGE RULE **MANDATORY**: You MUST respond in the SAME language as the user's question.

## Core Principles: Provide direct, factual answers with friendly words. Keep responses concise and focused on the specific question. If not having matching sources, you must response to user professionally, avoid letting the user lead the conversation.

## REMEMBER: Always match the user's language in your response. If having contact information sources, including link reference, you should combine it to response if needed"""

    @classmethod
    def build_user_prompt(cls, question: str, context: str, language: str) -> str:
        """Build user prompt with proper language instructions"""
        prompt_parts = []

        if language in ["vietnamese", "Vietnamese", "vi"]:
            prompt_parts.extend(
                [
                    "🚨 NGÔN NGỮ BẮT BUỘC: Bạn PHẢI trả lời hoàn toàn bằng tiếng Việt!",
                    "🚨 MANDATORY LANGUAGE: You MUST respond entirely in Vietnamese!",
                ]
            )
        else:
            prompt_parts.append(
                "🚨 MANDATORY LANGUAGE: You MUST respond entirely in English!"
            )

        prompt_parts.append("\n" + "=" * 60 + "\n")

        if context.strip():
            header = (
                "**Tài liệu tham khảo:**"
                if language == "vietnamese"
                else "**Reference Materials:**"
            )
            prompt_parts.extend([header, context, "\n" + "=" * 50 + "\n"])

        question_header = (
            "**Câu hỏi của người dùng:**"
            if language == "vietnamese"
            else "**User Question:**"
        )
        prompt_parts.append(f"{question_header} {question}")

        return "\n".join(prompt_parts)


class CallbackLLMService:
    """LLM service with optimized connection pooling"""

    def __init__(self, config: LLMConfiguration, callback_urls: Dict[str, str]):
        self.config = config
        self.callback_urls = callback_urls
        self.prompt_manager = PromptManager()

        # Optimized session with connection pooling
        self.session = requests.Session()

        retry_strategy = Retry(
            total=1,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
        )

        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=retry_strategy,
            pool_block=False,
        )

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }
        )

    def generate_response(
        self,
        session_id: str,
        question: str,
        context: str = "",
        language: str = "Vietnamese",
        history: Optional[list] = None,
        correlation_id: str = "",
    ) -> str:
        """Generate LLM response with optimized connection"""
        try:
            messages = self._build_messages(question, context, language, history)

            payload = {
                "session_id": session_id,
                "model": self.config.model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "top_p": self.config.top_p,
                "stream": False,
                "correlation_id": correlation_id or session_id,
            }

            stream_url = self.callback_urls.get("stream_llm")
            if not stream_url:
                raise ValueError("stream_llm callback URL not found")

            if not stream_url.startswith(("http://", "https://")):
                stream_url = f"http://{stream_url}"

            logger.info(f"🚀 Calling LLM service: {stream_url}")

            # Optimized timeout: (connect_timeout, read_timeout)
            response = self.session.post(stream_url, json=payload, timeout=(3, 90))
            response.raise_for_status()

            response_data = response.json()
            logger.info(
                f"📥 LLM response status: {response_data.get('status', 'unknown')}"
            )

            if not response_data.get("status"):
                error_msg = response_data.get("error", "LLM request failed")
                logger.error(f"❌ LLM request failed: {error_msg}")
                return self._get_fallback_response(question)

            response_text = response_data.get("result", {}).get("content", "")
            if not response_text:
                logger.warning("⚠️ Empty response from LLM service")
                return self._get_fallback_response(question)

            logger.info(f"✅ LLM response generated: {len(response_text)} chars")
            return response_text

        except requests.exceptions.Timeout as e:
            logger.error(f"⏰ LLM request timeout: {e}")
            return self._get_fallback_response(question)
        except requests.exceptions.RequestException as e:
            logger.error(f"🌐 HTTP error in LLM generation: {e}")
            return self._get_fallback_response(question)
        except Exception as e:
            logger.error(f"❌ LLM generation failed: {e}")
            return self._get_fallback_response(question)

    def _build_messages(
        self, question: str, context: str, language: str, history: Optional[list]
    ) -> list:
        """Build message array for LLM request"""
        messages = [{"role": "system", "content": self.prompt_manager.SYSTEM_PROMPT}]

        if history:
            for entry in history:
                if entry.get("role") in ["user", "assistant"]:
                    messages.append(
                        {"role": entry["role"], "content": entry["content"]}
                    )

        user_prompt = self.prompt_manager.build_user_prompt(question, context, language)
        messages.append({"role": "user", "content": user_prompt})

        return messages

    def _get_fallback_response(self, question: str) -> str:
        """Get fallback response when LLM fails"""
        is_vietnamese = LanguageDetector.detect_language(question) == "vietnamese"
        return (
            "Xin lỗi, hệ thống đang gặp sự cố kỹ thuật. Vui lòng thử lại sau."
            if is_vietnamese
            else "Sorry, the system is experiencing technical difficulties. Please try again later."
        )

    def __del__(self):
        """Cleanup session on deletion"""
        if hasattr(self, "session"):
            self.session.close()


def main(
    question: str,
    formatted_context: str,
    callback_urls_config: Dict[str, Any],
    language: str = "Vietnamese",
    history: Optional[list] = None,
    config: Optional[Dict] = None,
    session_id: str = "",
    correlation_id: str = "",
    workspace_path: str = "finops",
) -> str:
    """
    Main LLM service function with optimized connection pooling & timeouts

    Optimizations applied:
    - Connection pooling (10 connections, 20 max)
    - Retry strategy (1 retry with exponential backoff)
    - Optimized timeouts: 3s connect, 90s read
    - Persistent session reuse
    - GZIP compression support

    Args:
        question: User's question
        formatted_context: Context for RAG
        callback_urls_config: WebSocket callback URLs
        language: Response language preference
        history: Chat history
        config: LLM configuration
        session_id: Session identifier
        correlation_id: Request correlation ID
        workspace_path: Windmill workspace path

    Returns:
        Generated response text
    """

    # Generate correlation_id if not provided
    if not correlation_id:
        correlation_id = f"req_{session_id}_{int(time.time())}"

    logger.info("=" * 80)
    logger.info(f"🚀 Starting Optimized LLM Service")
    logger.info(f"   📝 Question: {question[:100]}...")
    logger.info(f"   🔗 Correlation ID: {correlation_id}")
    logger.info(f"   👤 Session ID: {session_id}")
    logger.info(f"   🏢 Workspace: {workspace_path}")
    logger.info("=" * 80)

    # Initialize status manager
    status_manager = None
    if callback_urls_config and callback_urls_config.get("update"):
        callback_base = callback_urls_config["update"].replace("/windmill/update", "")
        status_manager = WindmillStatusManager(
            callback_base=callback_base,
            correlation_id=correlation_id,
            workspace_path=workspace_path,
            session_id=session_id,
        )

    try:
        # Step 1: Initialize
        logger.info("📋 Step 1: Initializing LLM configuration")
        if status_manager:
            status_manager.notify_step_completion("initialization")

        # Build LLM configuration
        llm_config = LLMConfiguration(
            model=config.get("llm_model", "moonshotai/kimi-k2-instruct-0905")
            if config
            else "moonshotai/kimi-k2-instruct-0905",
            temperature=config.get("temperature", 0.6) if config else 0.6,
            max_tokens=config.get("max_tokens", 5000) if config else 5000,
        )

        logger.info(
            f"🔧 LLM Config: {llm_config.model} (temp={llm_config.temperature})"
        )

        # Step 2: Prepare request
        logger.info("🎯 Step 2: Preparing LLM request")
        if status_manager:
            status_manager.notify_step_completion("request_preparation")

        if not callback_urls_config:
            raise ValueError("callback_urls_config is required")

        # Create service instance
        service = CallbackLLMService(llm_config, callback_urls_config)

        # Step 3: Generate response
        logger.info("🧠 Step 3: Generating LLM response")
        if status_manager:
            status_manager.notify_step_completion("llm_generation")

        response = service.generate_response(
            session_id=session_id,
            question=question,
            context=formatted_context,
            language=language,
            history=history,
            correlation_id=correlation_id,
        )

        # Step 4: Finalize
        logger.info("✅ Step 4: Finalizing response")
        if status_manager:
            status_manager.notify_step_completion("finalization")

        logger.info("=" * 80)
        logger.info(f"✅ LLM Service completed successfully")
        logger.info(f"   📏 Response length: {len(response)} characters")
        logger.info(f"   ⏱️ Correlation ID: {correlation_id}")
        logger.info("=" * 80)

        return response

    except Exception as e:
        error_msg = f"LLM service failed: {str(e)}"
        logger.error("=" * 80)
        logger.error(f"❌ {error_msg}")
        logger.error(f"   🔗 Correlation ID: {correlation_id}")
        logger.error("=" * 80)

        # Notify error status
        if status_manager:
            status_manager.notify_step_completion("error")

        raise RuntimeError(error_msg)
