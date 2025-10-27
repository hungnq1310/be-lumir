# import wmill
import requests
import json

def main(user_id: str, session_id: str, user_message: str, assistant_message: str):
    """
    Save conversation history to the API endpoint.
    
    Args:
        user_id: The user's ID
        session_id: The session ID
        user_message: The user's message
        assistant_message: The assistant's response
    
    Returns:
        dict: The API response
    """
    # Get the API endpoint
    url = "http://192.168.2.130:2026/history/save"
    
    # Prepare the payload with the required parameters
    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "user_message": user_message,
        "assistant_message": assistant_message
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