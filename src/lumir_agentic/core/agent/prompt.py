from ...loader.prompt_loader import PromptLoader
import os
from pathlib import Path

# Create a global instance of PromptLoader with correct template directory
current_dir = Path(__file__).parent.parent
template_dir = current_dir / "prompt"
prompt_loader = PromptLoader(template_dir=str(template_dir))

def render_prompt(template_name: str, **kwargs) -> str:
    template = prompt_loader.load_template(template_name)
    return template.render(**kwargs)


def reasoning_prompt(user_question: str, conversation_history: str = "", user_profile: dict = None) -> str:
    """Prompt for reasoning step"""
    return render_prompt(
        "reasoning",
        user_question=user_question,
        conversation_history=conversation_history,
        user_profile=user_profile
    )

def planning_prompt(user_question: str, reasoning_result: str, available_tools: list, user_profile: dict = None) -> str:
    """Prompt for planning step"""
    return render_prompt(
        "planning",
        user_question=user_question,
        reasoning_result=reasoning_result,
        available_tools=available_tools,
        user_profile=user_profile
    )

def tool_execution_prompt(tool_name: str, parameters: dict, context: str) -> str:
    """Prompt for tool execution"""
    return render_prompt(
        "tool_execution",
        tool_name=tool_name,
        parameters=parameters,
        context=context
    )

def chat_generation_prompt(user_question: str, conversation_history: str, tool_results: list, language: str = "vietnamese", user_profile: dict = None) -> str:
    """Prompt for final response generation"""
    return render_prompt(
        "chat",
        user_question=user_question,
        conversation_history=conversation_history,
        tool_results=tool_results,
        language=language,
        user_profile=user_profile
    )


def memory_decision_prompt(user_question: str, memory_conversation: dict = None) -> str:
    """Prompt for memory decision"""
    return render_prompt(
        "memory",
        USER_QUESTION=user_question ,
        MEMORY_CONVERSATION=memory_conversation
    )


