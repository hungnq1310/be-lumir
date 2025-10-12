from typing import List, Dict, Any, Optional
from typing_extensions import Annotated, TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from dataclasses import dataclass


class ConversationMessage(BaseModel):
    """Single conversation message"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None


@dataclass
class ToolCall:
    tool_name: str
    parameters: dict
    result: str
    success: bool

class UseMemory(BaseModel):
    """User memory profile"""
    is_use_memory: bool = Field(default=False, description="Whether to use memory")


class ReasoningStep(BaseModel):
    """Single reasoning step"""
    step: str
    reasoning: str
    action: Optional[str] = None


class Plan(BaseModel):
    """Execution plan"""
    goal: str
    steps: List[ReasoningStep]
    tools_needed: List[str]


class WorkflowAgentState(TypedDict):
    """LangGraph state for Lumir Agent with proper annotations"""
    
    #########################
    #         INPUT         #
    #########################
    messages: Annotated[list, add_messages]
    conversation_history : List[ConversationMessage]
    user_profile: Optional[Dict[str, Any]]

    #########################
    #       PROCESSING      #
    #########################


    use_memory: UseMemory
    reasoning:List[ReasoningStep]
    plan: Optional[Plan]
    tools_called: List[ToolCall]

    #########################
    #          LLM          #
    #########################

    llm: Any

    #########################
    #        OUTPUT         #
    #########################

    final_response: str
    
    #########################
    #        CONTROL        #
    #########################

    current_step: str  # "reasoning", "planning", "tool_execution", "response_generation"
    is_complete: bool



class WorkflowChatState(TypedDict):
    """LangGraph state for Lumir Agent with proper annotations"""
    
    #########################
    #         INPUT         #
    #########################
    user_question: str  # Add missing user_question field
    messages: Annotated[list, add_messages]
    conversation_history : List[ConversationMessage]
    user_profile: Optional[Dict[str, Any]]

    #########################
    #       PROCESSING      #
    #########################

    use_memory: bool  # Change from UseMemory to bool for simplicity
    memory_context: Optional[str]  # Add memory_context field
    tool_calls: List[ToolCall]  # Add tool_calls field
    tool_results: Optional[str]  # Add tool_results field
    memory_conversation: Optional[Any]  # Add memory_conversation field

    #########################
    #          LLM          #
    #########################

    llm: Any

    #########################
    #        OUTPUT         #
    #########################

    final_response: str
    
    #########################
    #        CONTROL        #
    #########################

    current_step: str  # "reasoning", "planning", "tool_execution", "response_generation"
    is_complete: bool
