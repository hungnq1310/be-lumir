# import wmill
import requests
import json


def main(
    user_question: str,
    user_id: str,
    user_name: str,
    session_id: str,
    language: str = "vietnamese",
    history: list = None,
):
    """
    Send a chat request to the API endpoint.

    Args:
        user_question: The user's question
        user_id: The user's ID
        user_name: The user's name
        session_id: The session ID
        language: Language code (default: vietnamese)
        history: List of previous conversation history

    Returns:
        dict: The API response
    """
    # Get the API endpoint
    url = "http://192.168.2.130:2026/chat"

    # Prepare the payload with the required parameters
    payload = {
        "question": user_question,
        "user_id": user_id,
        "user_name": user_name,
        "session_id": session_id,
        "language": language,
        "history": history or [],
    }

    # Set headers
    headers = {"accept": "application/json", "Content-Type": "application/json"}

    try:
        # Make the POST request
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}
