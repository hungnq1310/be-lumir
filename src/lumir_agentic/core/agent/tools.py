import os
import sys
import json
from typing import Dict ,List, Any , Optional
import dotenv

from .states import WorkflowChatState

from langchain_core.tools import tool
from ...utils.keyword_TBI import get_keywords, KEYWORD
from ..tools.TBI_caculate import TBICalculator, get_TBI_data
from ..tools.trading_caculate import get_live_trading, LiveTrading, get_trade_account, TradeAccount, trade_hisory_report, TradeHistoryReport
from ..tools.search_rag import rag_query
from ...utils.logger import logger
from tabulate import tabulate

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
def format_live_trading_table(account_number: int, date_from: str = None, date_to: str = None, limit: int = None) -> str:
    """
    Lấy dữ liệu live trading và hiển thị dạng bảng

    Args:
        account_number (int): Số tài khoản giao dịch
        date_from (str, optional): Ngày bắt đầu (YYYY-MM-DD)
        date_to (str, optional): Ngày kết thúc (YYYY-MM-DD)
        limit (int, optional): Số lượng bản ghi tối đa

    Returns:
        str: Bảng dữ liệu live trading với các cột: ID, Symbol, Side, Volume, Entry Time, Entry Price, Pips, Profit, Balance, Equity
    """
    # Create LiveTrading object from parameters
    data = LiveTrading(
        account_number=account_number,
        date_from=date_from,
        date_to=date_to,
        limit=limit
    )

    # Get live trading data (raw JSON)
    response = get_live_trading(data)

    if not response.get('status') or not response.get('data', {}).get('data'):
        return "Không có dữ liệu giao dịch"

    trades = response['data']['data']
    if not trades:
        return "Không có giao dịch nào trong khoảng thời gian này"

    # Prepare table data with proper field mapping
    headers = ["ID", "Symbol", "Side", "Volume", "Entry Time", "Entry Price", "Pips", "Profit", "Balance", "Equity"]
    rows = []

    for trade in trades:
        # Parse position data if available
        position_data = {}
        if trade.get('position'):
            try:
                if isinstance(trade['position'], str):
                    position_data = json.loads(trade['position'])
                else:
                    position_data = trade['position']
            except:
                position_data = {}

        # Extract data from position or trade
        profit_val = position_data.get('profit') or trade.get('profit') or 0
        balance_val = trade.get('balance') or 0
        equity_val = trade.get('equity') or 0

        row = [
            trade.get('id', 'N/A'),
            position_data.get('symbol', 'N/A'),
            position_data.get('side', 'N/A'),
            f"{position_data.get('volume_lots', 0):.2f}" if position_data.get('volume_lots') else 'N/A',
            position_data.get('entry_time', trade.get('time', 'N/A'))[:19] if position_data.get('entry_time') else trade.get('time', 'N/A')[:19] if trade.get('time') else 'N/A',
            f"{position_data.get('entry_price', 0):.3f}" if position_data.get('entry_price') else 'N/A',
            f"{position_data.get('pips', 0):.1f}" if position_data.get('pips') else 'N/A',
            f"{float(profit_val):,.2f}",
            f"{float(balance_val):,.2f}",
            f"{float(equity_val):,.2f}"
        ]
        rows.append(row)
    account_number = f"ACCOUNT NUMER: {account_number}" + '\n'
    return account_number + tabulate(rows, headers=headers, tablefmt="grid", stralign="left", numalign="right")

@tool
def format_trade_account_table(user_id: str) -> str:
    """
    Lấy dữ liệu tài khoản giao dịch và hiển thị dạng bảng

    Args:
        user_id (str): ID của người dùng

    Returns:
        str: Bảng dữ liệu tài khoản với thông tin chi tiết và thống kê giao dịch
             Bảng chính: Account Number, Nickname, Broker, Platform, Type, Balance, Created At
             Thống kê: Today's Profit, Current Equity, Current Balance, Current P&L, Total Profit, Total Trades, Today's Trades, Open Positions, Open Orders
    """
    # Create TradeAccount object from parameter
    data = TradeAccount(user_id=user_id)

    # Get trade account data (raw JSON)
    response = get_trade_account(data)

    if not response.get('status') or not response.get('data', {}).get('items'):
        return "Không có dữ liệu tài khoản"

    accounts = response['data']['items']

    # Prepare table data for main account info
    headers = ["Account Number", "Nickname", "Broker", "Platform", "Type", "Created At"]
    rows = []

    for account in accounts:
        stats = account.get('trading_stats', {})
        # Get balance from trading_stats instead of account level for more accurate data
        row = [
            account.get('account_number', 'N/A'),
            account.get('nickname', 'N/A'),
            account.get('broker', 'N/A'),
            account.get('platform', 'N/A'),
            account.get('type', 'N/A'),
            account.get('created_at', 'N/A')[:19] if account.get('created_at') else 'N/A'
        ]
        rows.append(row)

    # Return only the main account table (trim stats as requested)
    account_table = tabulate(rows, headers=headers, tablefmt="grid", stralign="left", numalign="right")
    return account_table

@tool
def format_trade_history_table(account_number: int, date_from: str = None, date_to: str = None, symbol: str = None, side: str = None) -> str:
    """
    Lấy báo cáo lịch sử giao dịch và hiển thị dạng bảng

    Args:
        account_number (int): Số tài khoản giao dịch
        date_from (str, optional): Ngày bắt đầu (YYYY-MM-DD)
        date_to (str, optional): Ngày kết thúc (YYYY-MM-DD)
        symbol (str, optional): Symbol cặp tiền (ví dụ: "XAUUSDm")
        side (str, optional): Loại lệnh ("buy" hoặc "sell")

    Returns:
        str: Bảng báo cáo lịch sử giao dịch với các chỉ số: Total Trades, Today Balance, Net Profit Before Today,
             Today Permitted Loss, Max Permitted Loss, Initial Balance, Balance Size, Start Time, Last Updated, Net Profit Today
    """
    # Create TradeHistoryReport object from parameters
    kwargs = {
        'account_number': account_number,
        'date_from': date_from,
        'date_to': date_to
    }

    # Only add optional parameters if they're not None
    if symbol is not None:
        kwargs['symbol'] = symbol
    if side is not None:
        kwargs['side'] = side

    data = TradeHistoryReport(**kwargs)

    # Get trade history report data (raw JSON)
    response = trade_hisory_report(data)

    if not response:
        return "Không có dữ liệu báo cáo"

    headers = ["Metric", "Value"]
    rows = [
        ["account_id", f"{kwargs['account_number']}"],
        ["total_trades", f"{response.get('total_trades', 0):,.0f}"],
        ["today_balance", f"{response.get('today_balance', 0):,.2f}"],
        ["net_profit_before_today", f"{response.get('net_profit_before_today', 0):,.2f}"],
        ["today_permitted_loss", f"{response.get('today_permitted_loss', 0):,.2f}"],
        ["max_permitted_loss", f"{response.get('max_permitted_loss', 0):,.2f}"],
        ["balance_init", f"{response.get('balance_init', 0):,.2f}"],
        ["balance_size", f"{response.get('balance_size', 0):,.2f}" if response.get('balance_size') else "N/A"],
        ["start_time", response.get('start_time', 'N/A')],
        ["last_updated_time", response.get('last_updated_time', 'N/A')],
        ["net_profit_today", f"{response.get('net_profit_today', 0):,.2f}"]
    ]
    account_header = f"ACCOUNT NUMER: {kwargs['account_number']}" + '\n'
    return account_header + tabulate(rows, headers=headers, tablefmt="grid", stralign="left", numalign="right")



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
        "format_live_trading_table": {
            "description": "Hiển thị các lệnh trade đang mở/hoạt động của tài khoản. Dùng khi user hỏi 'đang có lệnh nào', 'các trade đang mở', 'hiện tại giao dịch gì'.",
            "input": {
                "account_number": {"type": "int", "description": "Số tài khoản giao dịch để xem các lệnh đang mở."},
                "date_from": {"type": "str", "description": "Ngày bắt đầu (YYYY-MM-DD) - tùy chọn, dùng để lọc theo khoảng thời gian."},
                "date_to": {"type": "str", "description": "Ngày kết thúc (YYYY-MM-DD) - tùy chọn, dùng để lọc theo khoảng thời gian."},
                "limit": {"type": "int", "description": "Số lượng bản ghi tối đa - tùy chọn."}
            }
        },
        "format_trade_account_table": {
            "description": "Liệt kê tất cả các tài khoản trade của user. Dùng khi user hỏi 'có những tài khoản nào', 'tài khoản trade', 'các account'.",
            "input": {
                "user_id": {"type": "str", "description": "ID của người dùng để xem danh sách các tài khoản trade."}
            }
        },
        "format_trade_history_table": {
            "description": "Tạo báo cáo hiệu năng trade tổng quan (lời/lỗ, số lượng giao dịch, v.v.). Dùng khi user hỏi 'hiệu năng trade', 'kết quả giao dịch', 'đánh giá tổng quan'.",
            "input": {
                "account_number": {"type": "int", "description": "Số tài khoản giao dịch để xem báo cáo hiệu năng."},
                "date_from": {"type": "str", "description": "Ngày bắt đầu (YYYY-MM-DD) - tùy chọn, dùng để lọc báo cáo theo khoảng thời gian."},
                "date_to": {"type": "str", "description": "Ngày kết thúc (YYYY-MM-DD) - tùy chọn, dùng để lọc báo cáo theo khoảng thời gian."},
                "symbol": {"type": "str", "description": "Symbol cặp tiền (ví dụ: XAUUSDm) - tùy chọn, dùng để lọc theo cặp tiền cụ thể."},
                "side": {"type": "str", "description": "Loại lệnh (buy hoặc sell) - tùy chọn, dùng để lọc theo loại lệnh."}
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
        format_live_trading_table,
        format_trade_account_table,
        format_trade_history_table,
        search_knowledge_base,
        get_mapping_keyword,
        get_memory_context
    ]

