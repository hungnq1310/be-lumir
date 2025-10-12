import json
from lumir_agentic.utils.logger import logger
import os
from typing import Dict , List , Any , Optional, Literal, Union
from utils.logger import logger, getlogger

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
        
        # Tạo prompt từ template memory.j2
        prompt = memory_decision_prompt(user_question=user_question, memory_conversation=memory_conversation)
        
        # Lấy LLM từ state
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
