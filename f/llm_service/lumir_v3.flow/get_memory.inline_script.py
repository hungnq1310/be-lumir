# requirements:
# requests

import requests
import json


def main(user_id: str, session_id: str):
    # Get history from the API
    url = "http://192.168.2.130:2026/history/get"

    payload = {"user_id": user_id, "session_id": session_id}

    headers = {"accept": "application/json", "Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}
