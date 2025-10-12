# import wmill
from typing import Dict
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# ACCOUNT_TRADING_ID = "9259692"
TRADING_SUMARYZE_URL = os.getenv("TRADING_ANALYZE_URL")
if not TRADING_SUMARYZE_URL:
    raise ValueError("TRADING_ANALYZE_URL environment variable is required")
TRADING_API_TIMEOUT = int(os.getenv("TRADING_API_TIMEOUT", "30"))


def test_get_api_indicator_trading(account_number: str, url: str):
    try:
        # Format the request to match the /trading endpoint expectations
        payload = {
            "user_question": f"Analyze trading data for account {account_number}",
            "account_number": account_number,
        }
        response = requests.post(url, json=payload, timeout=TRADING_API_TIMEOUT)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        return response.json()
    except requests.exceptions.ConnectionError:
        return {
            "error": "Connection failed",
            "detail": f"Could not connect to {url}. Make sure the server is running.",
        }
    except requests.exceptions.Timeout:
        return {
            "error": "Timeout",
            "detail": f"Request to {url} timed out after 30 seconds.",
        }
    except requests.exceptions.HTTPError as e:
        # Try to get more detailed error information
        try:
            error_detail = e.response.json() if e.response.content else e.response.text
        except Exception:
            error_detail = e.response.text if hasattr(e.response, "text") else str(e)
        return {
            "error": "HTTP Error",
            "detail": f"HTTP {e.response.status_code}: {error_detail}",
        }
    except requests.exceptions.RequestException as e:
        return {"error": "Request failed", "detail": str(e)}
    except ValueError:
        return {"error": "Invalid JSON", "detail": "Server response was not valid JSON"}


def parse_trading_data(data, heading=3):
    """Parse trading data and format it as markdown."""
    lines = ["## TRADING DATA"]

    def _format(obj, level):
        if isinstance(obj, dict):
            for k, v in obj.items():
                lines.append(f"{'#' * level} {k}")
                _format(v, level + 1)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    _format(item, level)
                else:
                    indent = "  " * (level - 2) if level >= 2 else ""
                    lines.append(f"{indent}- {item}")
        else:
            indent = ""  # không indent thêm cho giá trị đơn
            lines.append(f"{indent}{obj}")

    _format(data, heading)
    return "\n\n".join(lines)


def get_trading_data(config: Dict):
    """
    Function to get trading data.
    """
    docs = test_get_api_indicator_trading(config["account_number"], config["url"])
    formatted_docs = parse_trading_data(docs)
    return formatted_docs


if __name__ == "__main__":
    print(TRADING_SUMARYZE_URL)
    config = {
        "account_number": "9259692",
        "url": TRADING_SUMARYZE_URL,
    }
    trading_data = get_trading_data(config)
    print(trading_data)


