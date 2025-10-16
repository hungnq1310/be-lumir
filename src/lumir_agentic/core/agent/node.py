import json
from lumir_agentic.utils.logger import logger
import os
import asyncio
from typing import Dict , List , Any , Optional, Literal, Union
from lumir_agentic.core.agent.memory import EncryptedMemoryManager
from dotenv import load_dotenv

from .states import WorkflowAgentState, WorkflowChatState, ReasoningStep, ToolCall, Plan, UseMemory
from .prompt import build_langchain_template
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI

from .prompt import (
    planning_prompt,
    memory_decision_prompt, 
    reasoning_agent_prompt,
    agent_generation_system_prompt,
    agent_use_tools_prompt
  
)

from .tools import (
    search_knowledge_base,
    calculate_tbi_indicators,
    get_mapping_keyword,
    get_memory_context,
    format_live_trading_table,
    format_trade_account_table,
    format_trade_history_table,
    TOOL_DESCRIPTION
)


load_dotenv()

LIMIT_CHAT = int(os.getenv("LIMIT_CHAT", 5))

def reasoning_agent_node(state: WorkflowAgentState):
    """
    Phân tích dựa trên context cung cấp và đưa ra những quyết định sử dụng  những nguồn gì để đáp ứng câu hỏi của user.
    """
    # Sử dụng conversation_history thay vì memory_conversation cho agent flow
    conv_history = state.get("conversation_history", [])
    system_prompt = reasoning_agent_prompt(
        user_info=state.get("user_info"),
        conversation_history=str(conv_history),
        tools=TOOL_DESCRIPTION,
        user_question=state.get("user_question", ""),
    )


    messages = build_langchain_template(
        user_input=state.get("user_question", ""),
        conversation_history=[], # when using memory conversation , it conflict with output format reasoning agent
        system_prompt=system_prompt,
    )
    llm = state.get("llm")
    if not llm:
        raise ValueError("LLM not found in state")
    response = llm.invoke(messages)
    return response



def execute_tool_calls(response_message, tool_registry: dict) -> dict:
    """
    Execute all tool_calls from the model's response message.
    Return results as a dictionary {tool_name: output}.
    """
    results = {}
    tool_calls = getattr(response_message, "tool_calls", [])

    if not tool_calls:
        return {"info": "No tool calls found in response."}

    for call in tool_calls:
        tool_name = call.get("name")
        tool_args = call.get("args", {})
        func = tool_registry.get(tool_name)

        if not func:
            results[tool_name] = f"⚠️ Tool '{tool_name}' chưa được đăng ký."
            continue

        try:
            result = func.invoke(tool_args) 
            results[tool_name] = result
        except Exception as e:
            results[tool_name] = f"❌ Error executing {tool_name}: {str(e)}"

    return results



def chat_plan(state: WorkflowChatState, conversation_history:List[Dict], user_question:str):

    system_prompt = planning_prompt("chat_plan")
    messages = build_langchain_template(user_input=user_question, 
                                        conversation_history=conversation_history, 
                                        system_prompt=system_prompt)
    llm = state.get("llm")
    if not llm:
        raise ValueError("LLM not found in state")

    response = llm.invoke(messages)
    plan = response.content.strip()
    return plan

    
def use_tools(state: Union[WorkflowChatState, WorkflowAgentState]):

    # Get llm
    llm = state.get("llm")
    if not llm:
        raise ValueError("LLM not found in state")

    # Get plan
    plan = state.get("plan")
    if not plan:
        raise ValueError("Plan not found in state")

    list_tools = state.get("list_tools", [])
    if not list_tools:
        raise ValueError("List tools not found in state")
    # Build system prompt to enforce mapping → RAG policy for definition queries
    system_prompt = agent_use_tools_prompt(
        user_question=state.get("user_question", ""),
        reasoning=plan,
        tools=TOOL_DESCRIPTION,
    )

    model_with_tools = llm.bind_tools(list_tools)
    response = model_with_tools.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=plan)
    ])
    logger.info(f"Chat Plan Node - Generated Response: {response.content.strip()}")
    
    # create tools_registry base on name of list_tools
    tool_registry = {}
    for tool in list_tools:
        # Get tool name from the function name if name attribute is not available
        if hasattr(tool, 'name'):
            tool_name = tool.name
        else:
            tool_name = tool.__name__
        tool_registry[tool_name] = tool
    
    tool_results = execute_tool_calls(response, tool_registry)
    # logger.info(f"Chat Plan Node - Tool Results: {tool_results}")
    
    return tool_results
    

    

def agent_plan(state:WorkflowAgentState):
    pass



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
        memory_conversation = state.get("memory_conversation", [])        
        prompt = memory_decision_prompt(user_question=user_question, memory_conversation=memory_conversation)
        
        llm = state.get("llm")
        if not llm:
            raise ValueError("LLM not found in state")

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




