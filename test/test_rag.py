

import os
import sys
from dotenv import load_dotenv
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

# Add project path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
from lumir_agentic.utils.keyword_TBI import get_keywords
from lumir_agentic.core.tools.search_rag import rag_query

# === 1. Load env ===
load_dotenv()
MODEL_NAME = os.getenv("MODEL_NAME")
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")

# === 2. Init model ===
system_prompt = """Bạn là một trợ lý AI thông minh. 
Khi người dùng hỏi về ý nghĩa của từ viết tắt, thuật ngữ chuyên môn, 
hoặc từ khóa không rõ nghĩa, hãy LUÔN sử dụng tool get_mapping_keyword để tra cứu định nghĩa chính xác từ cơ sở dữ liệu. 
Đối với MỌI câu hỏi định nghĩa (bao gồm cả từ viết tắt), hãy LUÔN sử dụng tool search_knowledge_base để cung cấp thông tin chi tiết.
Khi người dùng hỏi về thông tin chi tiết, giải thích khái niệm chung, hoặc các câu hỏi cần tra cứu trong cơ sở dữ liệu kiến thức tổng quát, hãy sử dụng tool search_knowledge_base.
Khi người dùng hỏi về thông tin cụ thể từ cơ sở dữ liệu của Lumir, đặc biệt là các báo cáo tài chính hoặc dữ liệu công ty, hãy sử dụng tool rag_lumir.
Nếu một câu hỏi yêu cầu cả định nghĩa và thông tin chi tiết (từ kiến thức tổng quát hoặc từ Lumir), ví dụ như 'X là gì và hãy nói thêm về nó?', hãy LUÔN sử dụng kết hợp các công cụ phù hợp: get_mapping_keyword cho định nghĩa và search_knowledge_base (hoặc rag_lumir) cho thông tin chi tiết để cung cấp câu trả lời toàn diện nhất.
"""

llm = ChatOpenAI(
    model_name=MODEL_NAME,
    openai_api_key=API_KEY,
    base_url=BASE_URL,
    temperature=0
)

# === 3. Define tools ===
@tool
def get_weather(location: str):
    """Call to get the current weather."""
    if location.lower() in ["sf", "san francisco"]:
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."

@tool
def get_coolest_cities():
    """Get a list of coolest cities"""
    return "nyc, sf"

@tool
def get_mapping_keyword(keyword: List[str]) -> Dict[str, Any]:
    """
    Tra cứu định nghĩa của các từ khóa, viết tắt hoặc thuật ngữ chuyên môn.
    Tool này CHỈ cung cấp định nghĩa ngắn gọn và cần kết hợp với search_knowledge_base để cung cấp thông tin chi tiết.
    Đối với MỌI câu hỏi định nghĩa, kể cả từ viết tắt như 'What is TBI?', hãy LUÔN sử dụng cả tool này VÀ search_knowledge_base.
    """
    return get_keywords(keyword_list=keyword)


@tool
def search_knowledge_base(question: str, top_n: int = 10, score_threshold: float = 0.5) -> Dict[str, Any]:
    """
    Tìm kiếm thông tin chi tiết, giải thích khái niệm chung, hoặc các câu hỏi cần tra cứu trong cơ sở dữ liệu kiến thức tổng quát.
    Sử dụng tool này khi người dùng hỏi các câu hỏi như "Giải thích về X", "Thông tin về Y", "X là gì?" (khi X không phải là từ viết tắt đơn thuần), hoặc khi cần thông tin chi tiết về một chủ đề rộng.
    Sử dụng tool này cho MỌI câu hỏi định nghĩa, kể cả từ viết tắt như 'What is TBI?', để cung cấp thông tin chi tiết bổ sung.
    Args:
        question: Câu hỏi cần tìm kiếm
        top_n: Số lượng kết quả trả về tối đa
        score_threshold: Ngưỡng điểm số tối thiểu
    
    Returns:
        Dict chứa kết quả tìm kiếm
    """
    try:
        # Sử dụng rag_query thực tế
        contexts = rag_query(
            question=question,
            top_n=top_n,
            score_threshold=score_threshold,
            include_full_details=True
        )
        
        return {
            "success": True,
            "data": contexts,
            "message": f"Knowledge base search completed successfully. Found {len(contexts)} results."
        }
    except Exception as e:
        return {
            "success": False,
            "data": [],
            "message": f"Knowledge base search failed: {str(e)}",
            "error": str(e)
        }


@tool
def rag_lumir(query: str) -> str:
    """
    Sử dụng RAG để tra cứu thông tin từ cơ sở dữ liệu Lumir.
    Sử dụng tool này khi người dùng hỏi các câu hỏi liên quan đến dữ liệu hoặc thông tin cụ thể có trong hệ thống Lumir, đặc biệt là các báo cáo tài chính, dữ liệu công ty, hoặc các thông tin nội bộ khác của Lumir.
    """
    return "RAG result for: " + query

# === 4. Bind model with tools ===
model_with_tools = llm.bind_tools([
    get_weather,
    get_coolest_cities,
    get_mapping_keyword,
    search_knowledge_base,
    rag_lumir
])

# === 5. Hàm thực thi tool_calls thủ công ===
def execute_tool_calls(response_message, tool_registry: dict) -> dict:
    """
    Thực thi tất cả tool_calls từ message trả về của model.
    Trả kết quả dạng dictionary {tool_name: output}.
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
            result = func.invoke(tool_args) # Sử dụng func.invoke(tool_args) để truyền các đối số
            results[tool_name] = result
        except Exception as e:
            results[tool_name] = f"❌ Error executing {tool_name}: {str(e)}"

    return results

tool_registry = {
    "get_weather": get_weather,
    "get_coolest_cities": get_coolest_cities,
    "get_mapping_keyword": get_mapping_keyword,
    "search_knowledge_base": search_knowledge_base,
    "rag_lumir": rag_lumir,
}

# Test cases for get_mapping_keyword and search_knowledge_base
test_questions = [
    ("What is TBI?", ["get_mapping_keyword", "search_knowledge_base"]),
    ("What is PPA?", ["get_mapping_keyword", "search_knowledge_base"]),
    ("Giải thích về Machine Learning", ["search_knowledge_base"]),
    ("Thông tin về thị trường chứng khoán", ["search_knowledge_base"]),
    ("Tóm tắt báo cáo tài chính của công ty X", ["rag_lumir"]),
    ("TBI là gì và hãy nói thêm về nó?", ["get_mapping_keyword", "search_knowledge_base"]),
]

for question, expected_tools in test_questions:
    print(f"\n--- Testing question: {question} ---")
    response_message = model_with_tools.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=question)
    ])

    if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
        called_tool_names = [call['name'] for call in response_message.tool_calls]
        print(f"LLM called tools: {called_tool_names}")
        
        # Check if all expected tools were called
        all_expected_tools_called = all(tool in called_tool_names for tool in expected_tools)
        
        if all_expected_tools_called and len(called_tool_names) == len(expected_tools):
            print("All expected tools were called.")
            results = execute_tool_calls(response_message, tool_registry)
            print(f"Tool execution result: {results}")
        else:
            print(f"ERROR: Expected tools {expected_tools} but got {called_tool_names}")
    else:
        print(f"LLM responded directly: {response_message.content}")
        if not expected_tools:
            print("Direct response is expected.")
        else:
            print(f"ERROR: Expected tool calls {expected_tools} but got direct response.")