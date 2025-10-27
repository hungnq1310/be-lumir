# import wmill
import requests
import json

def main(user_question:str,user_id:str,session_id:str,full_name:str,birthday:str,account_id:str,history:list):
    # Get the API endpoint
    url = "http://192.168.2.130:2026/agent"
    
    # Prepare the payload with flow inputs
    payload = {
        "question": user_question,
        "user_id": user_id,
        "session_id": session_id,
        "full_user_name": full_name,
        "birthday": birthday,
        "language": "vietnamese",
        "account_trading_id": account_id,
        "history": []
    }
    
    # Set headers
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    
    try:
        # Make the POST request
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}