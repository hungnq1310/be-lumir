from ...loader.prompt_loader import PromptLoader
import os
from pathlib import Path
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import List, Dict , Union, Literal

# Create a global instance of PromptLoader with correct template directory
current_dir = Path(__file__).parent.parent
template_dir = current_dir / "prompt"
prompt_loader = PromptLoader(template_dir=str(template_dir))

def render_prompt(template_name: str, **kwargs) -> str:
    template = prompt_loader.load_template(template_name)
    return template.render(**kwargs)



def build_langchain_template(user_input:str, conversation_history:List[Dict], system_prompt:str):

    messages = [SystemMessage(content=system_prompt)]
    for m in conversation_history:
        if len(conversation_history) > 0:
            if m["role"] == "user":
                messages.append(HumanMessage(content=m["content"]))
            else:
                messages.append(AIMessage(content=m["content"]))
    messages.append(HumanMessage(content=user_input))
    return messages


def reasoning_prompt(user_question: str, conversation_history: str = "", user_profile: dict = None) -> str:
    """Prompt for reasoning step"""
    return render_prompt(
        "reasoning",
        user_question=user_question,
        conversation_history=conversation_history,
        user_profile=user_profile
    )

def planning_prompt(planning_prompt_type: Literal["chat_plan", "agent_plan"],
) -> str:
    """Prompt for planning step"""
    return render_prompt(
        planning_prompt_type
    )

def chat_generation_system_prompt(tool_results: list, language: str = "vietnamese", user_profile: dict = None) -> str:
    """Prompt for final response generation"""
    return render_prompt(
        "chat",
        tool_results=tool_results,
        language=language,
        user_profile=user_profile
    )

def agent_generation_system_prompt(tool_result: List, language: str = "vietnamese", user_profile: dict = None):
    """Prompt cho phần sinh phản hồi của agent, nhận danh sách kết quả tool."""
    return render_prompt(
        "agent_response",
        tool_results=tool_result, 
        language=language,
        user_profile=user_profile,
    )




def reasoning_agent_prompt(
    user_info: Dict,
    conversation_history: str = "",
    tools: List = None,
    user_question: str = "",
) -> str:
    """Prompt cho bước reasoning của agent, hỗ trợ truyền danh sách tools."""
    return render_prompt(
        "reasoning",
        USER_INFO=user_info,
        CONVERSATION_HISTORY=conversation_history,
        TOOLS_LIST=tools,
        USER_QUESTION=user_question,
    )


def agent_use_tools_prompt(
    user_question: str,
    reasoning: str = "",
    tools: List = None,
) -> str:
    """Prompt cho bước thực thi tools của agent, áp dụng chính sách gọi mapping trước rồi RAG."""
    return render_prompt(
        "agent_use_tools",
        USER_QUESTION=user_question,
        REASONING=reasoning,
        TOOLS_LIST=tools,
    )


def memory_decision_prompt(user_question: str, memory_conversation: dict = None) -> str:
    """Prompt for memory decision"""
    return render_prompt(
        "memory",
        USER_QUESTION=user_question ,
        MEMORY_CONVERSATION=memory_conversation
    )



def tool_execution_prompt(tool_name: str, parameters: dict, context: str) -> str:
    """Prompt for tool execution"""
    return render_prompt(
        "tool_execution",
        tool_name=tool_name,
        parameters=parameters,
        context=context
    )