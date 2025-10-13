import json
from lumir_agentic.utils.logger import logger
import os
import asyncio
from typing import Dict , List , Any , Optional, Literal, Union
from lumir_agentic.core.agent.memory import EncryptedMemoryManager
from dotenv import load_dotenv

from .states import WorkflowAgentState, WorkflowChatState, ReasoningStep, ToolCall, Plan, UseMemory
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI

from .prompt import (
    reasoning_prompt,
    planning_prompt,
    tool_execution_prompt,
    memory_decision_prompt
    
)

from .tools import (
    search_knowledge_base,
    calculate_tbi_indicators,
    get_trading_analysis,
    get_mapping_keyword,
    get_memory_context
)


load_dotenv()

LIMIT_CHAT = int(os.getenv("LIMIT_CHAT", 5))



def memory_decision_node(state: Union[WorkflowChatState, WorkflowAgentState]) -> bool:
    """
    Quyết định có cần sử dụng memory hay không dựa trên câu hỏi của user.
    
    Args:
        state: WorkflowChatState hoặc WorkflowAgentState chứa user_question và memory_conversation
        
    Returns:
        bool: True nếu cần sử dụng memory, False nếu không cần
    """
    logger.info(f"Memory Decision Node - Analyzing if memory is needed")

    try:
        user_question = state["user_question"]
        memory_conversation = state.memory_conversation        
        prompt = memory_decision_prompt(user_question=user_question, memory_conversation=memory_conversation)
        
        llm = state.get("llm")
        if not llm:
            raise ValueError("LLM not found in state")

        # Gọi LLM để quyết định
        response = llm.invoke(prompt)
        decision_text = response.content.strip().lower()
        
        # Template trả về "true" hoặc "false" (không phải "yes"/"no")
        memory_decision = decision_text == "true"
        
        logger.info(f"Memory Decision Node - LLM Response: '{decision_text}'")
        logger.info(f"Memory Decision Node - Memory needed: {memory_decision}")
        
        return memory_decision
        
    except Exception as e:
        logger.error(f"Error in Memory Decision Node: {e}")
        # Trả về False thay vì raise để không crash workflow
        return False


async def get_history(user_id: str, session_id: str, limit: int = LIMIT_CHAT) -> List[Dict[str, Any]]:
    """
    Retrieve conversation history for a user session.
    
    Args:
        user_id: The user identifier
        session_id: The session identifier
        
    Returns:
        List of conversation items, empty list if session doesn't exist
    """
    try:
        logger.info(f"Getting history for user {user_id}, session {session_id}")
        
        # Create memory manager with combined session ID
        combined_session_id = f"{user_id}_{session_id}"
        logger.info(f"Combined session ID: {combined_session_id}")
        memory_manager = EncryptedMemoryManager(
            session_id=combined_session_id,
            ttl=864000  # 10 days TTL - match save_history TTL
        )
        
        # Create encrypted session (default to SQLite)
        encrypted_session = await memory_manager.create_encrypted_session("sqlite")
        
        # Get all items from the session
        items = await encrypted_session.get_items(limit=limit)
        
        logger.info(f"Retrieved {len(items)} items from session {session_id}")
        logger.info(f"Items content: {items}")
        return items
        
    except Exception as e:
        logger.error(f"Error getting history for user {user_id}, session {session_id}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []


async def save_history(user_id: str, session_id: str, user_message: str, assistant_message: str) -> bool:
    """
    Save user and assistant messages to the session.
    
    Args:
        user_id: The user identifier
        session_id: The session identifier
        user_message: The user's message
        assistant_message: The assistant's response
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Saving history for user {user_id}, session {session_id}")
        
        # Create memory manager with combined session ID
        combined_session_id = f"{user_id}_{session_id}"
        memory_manager = EncryptedMemoryManager(
            session_id=combined_session_id,
            ttl=864000  # 24 hours TTL
        )
        
        # Create encrypted session (default to SQLite)
        encrypted_session = await memory_manager.create_encrypted_session("sqlite")
        
        # Prepare conversation items
        conversation_items = [
            {"role": "user", "content": user_message, "timestamp": asyncio.get_event_loop().time()},
            {"role": "assistant", "content": assistant_message, "timestamp": asyncio.get_event_loop().time()}
        ]
        
        # Add items to the session
        await encrypted_session.add_items(conversation_items)
        
        # Verify items were added
        verification_items = await encrypted_session.get_items()
        logger.info(f"Verification: {len(verification_items)} items in session after save")
        
        logger.info(f"Successfully saved conversation to session {session_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving history for user {user_id}, session {session_id}: {e}")
        return False