import os
import sys
from typing import Dict ,List, Any , Optional
import dotenv

from .states import WorkflowChatState

from langchain_core.tools import tool
from ...utils.keyword_TBI import get_keywords, KEYWORD
from ..tools.TBI_caculate import TBICalculator, get_TBI_data
from ..tools.trading_caculate import get_trading_data
from ..tools.search_rag import rag_query
from ...utils.logger import logger

#####################
#   LOAD ENV CONFIG #
#####################

dotenv.load_dotenv()

@tool
def calculate_tbi_indicators(full_name: str, 
                             birthday: str) -> Dict[str, Any]:
    """
    Tính toán các chỉ số TBI (Trading Behavior Intelligence) dựa trên tên và ngày sinh.
    
    Args:
        full_name: Tên đầy đủ của người dùng
        birthday: Ngày sinh theo định dạng DD/MM/YYYY
    
    Returns:
        Dict chứa các chỉ số TBI đã tính toán
    """
    try:
        tbi_data = get_TBI_data(
            question="Tính toán chỉ số TBI",
            dob=birthday,
            name=full_name
        )
        
        results = tbi_data
        
        return {
            "success": True,
            "data": results,
            "message": "TBI indicators calculated successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to calculate TBI indicators"
        }


@tool
def get_trading_analysis(account_number: str) -> Dict[str, Any]:
    """
    Lấy và phân tích dữ liệu giao dịch chi tiết từ API trading.

    Tool này sẽ truy xuất TRỰC TIẾP từ hệ thống trading và trả về:
    - Tổng số giao dịch
    - Win rate, profit factor
    - Lãi/lỗ trung bình
    - Phân tích theo thời gian, symbol, side
    - Risk metrics và drawdown

    QUAN TRỌNG: Luôn gọi tool này khi user hỏi về lịch sử trading, portfolio,
    hoặc phân tích giao dịch. KHÔNG dựa vào conversation history cũ.

    Args:
        account_number: Số tài khoản giao dịch (lấy từ user_profile)

    Returns:
        Dict chứa dữ liệu phân tích giao dịch chi tiết
    """
    try:
        logger.system_info(f"[TOOL] get_trading_analysis called for account: {account_number}")

        # Use get_trading_data function
        config = {
            "account_number": account_number,
            "url": os.getenv("TRADING_ANALYZE_URL", "http://localhost:8081/analyze_trading")
        }

        logger.system_info(f"[TOOL] Calling trading API at: {config['url']}")
        trading_data = get_trading_data(config)

        logger.system_info(f"[TOOL] Trading data retrieved successfully: {len(str(trading_data))} chars")

        return {
            "success": True,
            "data": trading_data,
            "message": "Trading data retrieved successfully"
        }
    except Exception as e:
        logger.system_error(f"[TOOL] get_trading_analysis ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        logger.system_error(f"[TOOL] Traceback: {traceback.format_exc()}")

        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "message": "Failed to retrieve trading data"
        }



@tool
def search_knowledge_base(question: str, top_n: int = 10, score_threshold: float = 0.5) -> Dict[str, Any]:
    """
    Tìm kiếm thông tin trong knowledge base bằng RAG.
    
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
def get_mapping_keyword(keyword: List[str]) -> Dict[str, Any]:
    """
    Lấy từ khóa tương ứng từ danh sách các từ khóa đã định nghĩa.
    Args:
        keyword: Danh sách từ khóa cần tra cứu
    Returns:
        Dict chứa từ khóa và ý nghĩa tương ứng
    """
    return get_keywords(list(keyword))

def get_memory_context(state: WorkflowChatState):
    """
    Retrieves the memory context for the current conversation.
    """
    return state.get("memory_conversation", "")

TOOL_DESCRIPTION = """

     {
        "calculate_tbi_indicators": {
            "description": "Tính toán các chỉ số TBI (Trading Behavior Intelligence) dựa trên tên và ngày sinh.",
            "input": {
                "full_name": {"type": "str", "description": "Tên đầy đủ của người dùng."},
                "birthday": {"type": "str", "description": "Ngày sinh theo định dạng DD/MM/YYYY."},
            }
        },
        "get_trading_analysis": {
            "description": "Lấy và phân tích dữ liệu giao dịch chi tiết từ API trading.",
            "input": {
                "account_number": {"type": "str", "description": "Số tài khoản giao dịch (lấy từ user_profile)."}
            }
        },
        "search_knowledge_base": {
            "description": "Tìm kiếm thông tin trong knowledge base bằng RAG.",
            "input": {
                "question": {"type": "str", "description": "Câu hỏi cần tìm kiếm."},
                "top_n": {"type": "int", "description": "Số lượng kết quả trả về tối đa (auto top_k = 5)."},
                "score_threshold": {"type": "float", "description": "Ngưỡng điểm tin cậy (auto = 0.3)."}
            }
        },
        "get_mapping_keyword": {
            "description": "Lấy từ khóa tương ứng từ danh sách các từ khóa đã định nghĩa.",
            "input": {
                "keyword": {"type": "List[str]", "description": "Danh sách từ khóa cần tra cứu."}
            }
        }
    }

"""


def get_tools():
    """
    Trả về danh sách tất cả các công cụ có sẵn.
    Returns:
        List các công cụ langchain
    """
    return [
        calculate_tbi_indicators,
        get_trading_analysis,
        search_knowledge_base,
        get_mapping_keyword,
        get_memory_context
    ]

