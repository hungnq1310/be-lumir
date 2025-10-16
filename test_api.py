import requests
from dotenv import load_dotenv
import os
from typing import Literal
from tabulate import tabulate
import json

load_dotenv()

TOKEN_LUMIR = os.getenv("LUMIR_TOKEN_AUTHEN")
live_trading_url = "https://lumir-api.wealthfarming.org/api/v1/live-trading"
account_trade_url = "https://lumir-api.wealthfarming.org/api/v1/be/trade_accounts"
trade_history_url = "https://lumir-api.wealthfarming.org/api/v1/be/trade-history/reports"
headers = {
    f"Authorization": "Bearer " + TOKEN_LUMIR
}

from pydantic import BaseModel

class LiveTrading(BaseModel):
    account_number: int
    date_from:str = None
    date_to:str = None 
    limit: int = None

class TradeAccount(BaseModel):
    user_id:str

class TradeHistoryReport(BaseModel):
    account_number : int
    date_from:str = None
    date_to : str = None
    symbol : str  = None
    side : Literal["buy", "sell"] = None

def get_live_trading(data: LiveTrading):
    params = data.model_dump(exclude_none=True)
    response = requests.get(live_trading_url, headers=headers, params=params)
    return response.json()

def get_trade_account(data: TradeAccount):
    params = data.model_dump(exclude_none=True)
    response = requests.get(account_trade_url, headers=headers, params=params)
    return response.json()

def trade_hisory_report(data: TradeHistoryReport):
    params = data.model_dump(exclude_none=True)
    response = requests.get(trade_history_url, headers=headers, params=params)

    # how to remove key timeseries_by_trades from response.json()["data"]
    # drop key is : timeseries_by_trades, journal_closed_trades, chart_data, balance_data, drawdown_data, hourly_performance, raw_trades
    data = response.json()["data"]
   
    # return  data with key: total_trades, today_balance, net_profit_before_today, today_permitted_loss, max_permitted_loss, balance_init, balance_size, start_time, last_updated_time, net_profit_today, consistency_score. abs_most_result_day, abs_result_all_trading_day, mean_profitable, mean_loss, mean_RRR, sum_profitable, sum_loss, sum_volume, sum_net_profit,win_rate, profit_factor, sharpe_ratio, expectancy, max_daily_loss,max_loss
   
    
    data_clearn = {
        "total_trades": data["total_trades"],
        "today_balance": data["today_balance"],
        "net_profit_before_today": data["net_profit_before_today"],
        "today_permitted_loss": data["today_permitted_loss"],
        "max_permitted_loss": data["max_permitted_loss"],
        "balance_init": data["balance_init"],
        "balance_size": data["balance_size"],
        "start_time": data["start_time"],
        "last_updated_time": data["last_updated_time"],
        "net_profit_today": data["net_profit_today"],
    }
    return data_clearn

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

    # Get live trading data
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

    return tabulate(rows, headers=headers, tablefmt="grid", stralign="left", numalign="right")

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

    # Get trade account data
    response = get_trade_account(data)

    if not response.get('status') or not response.get('data', {}).get('items'):
        return "Không có dữ liệu tài khoản"

    accounts = response['data']['items']

    # Prepare table data for main account info
    headers = ["Account Number", "Nickname", "Broker", "Platform", "Type", "Balance", "Created At"]
    rows = []

    for account in accounts:
        row = [
            account.get('account_number', 'N/A'),
            account.get('nickname', 'N/A'),
            account.get('broker', 'N/A'),
            account.get('platform', 'N/A'),
            account.get('type', 'N/A'),
            f"{account.get('balance', 0):,.2f}",
            account.get('created_at', 'N/A')[:19] if account.get('created_at') else 'N/A'
        ]
        rows.append(row)

    account_table = tabulate(rows, headers=headers, tablefmt="grid", stralign="left", numalign="right")

    # Add trading stats for each account
    result = account_table + "\n\n"

    for i, account in enumerate(accounts, 1):
        stats = account.get('trading_stats', {})
        stats_headers = ["Metric", "Value"]
        stats_rows = [
            ["todays_profit", f"{float(stats.get('todays_profit', 0)):,.2f}"],
            ["current_equity", f"{float(stats.get('current_equity', 0)):,.2f}"],
            ["current_balance", f"{float(stats.get('current_balance', 0)):,.2f}"],
            ["current_pnl", f"{float(stats.get('current_pnl', 0)):,.2f}"],
            ["total_profit", f"{float(stats.get('total_profit', 0)):,.2f}"],
            ["total_trades", f"{int(stats.get('total_trades', 0)):,}"],
            ["todays_trades", f"{int(stats.get('todays_trades', 0)):,}"],
            ["open_positions", f"{int(stats.get('open_positions', 0)):,}"],
            ["open_orders", f"{int(stats.get('open_orders', 0)):,}"]
        ]

        result += f"Account {i} Trading Stats:\n"
        result += tabulate(stats_rows, headers=stats_headers, tablefmt="grid", stralign="left") + "\n\n"

    return result

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

    # Get trade history report data
    response = trade_hisory_report(data)

    if not response:
        return "Không có dữ liệu báo cáo"

    headers = ["Metric", "Value"]
    rows = [
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

    return tabulate(rows, headers=headers, tablefmt="grid", stralign="left", numalign="right")



if __name__ == "__main__":
    # Test format_live_trading_table với tham số riêng lẻ
    print("=" * 60)
    print("LIVE TRADING TABLE")
    print("=" * 60)
    print(format_live_trading_table(
        account_number=272515048,
        date_from="2025-10-15",
        date_to="2025-10-16",
        limit=10
    ))
    print()

    # Test format_trade_account_table với tham số riêng lẻ
    print("=" * 60)
    print("TRADE ACCOUNT TABLE")
    print("=" * 60)
    print(format_trade_account_table(user_id="1709"))
    print()

    # Test format_trade_history_table với tham số riêng lẻ
    print("=" * 60)
    print("TRADE HISTORY REPORT TABLE")
    print("=" * 60)
    print(format_trade_history_table(
        account_number=272515048,
        date_from="2025-10-01",
        date_to="2025-10-15"
    ))

# v1/be/trade-history/reports?account_number=9265433

# data2 = requests.get("https://ftmo-api-dev.buso.asia/api/v1/be/trade-history/reports", headers=headers, params={"account_number": "1709"}).json()
# print(data2['data'])

