# import wmill
from typing import Dict, List
import requests
import os
from dotenv import load_dotenv
import os 
from dotenv import load_dotenv

load_dotenv()

URL_LUMIR_RAG = os.getenv("RAG_QUERY_URL")
if not URL_LUMIR_RAG:
    raise ValueError("RAG_QUERY_URL environment variable is required")


def rag_query(
    question: str,
    top_n: int = 10,
    score_threshold: float = 0.5,
    include_full_details: bool = False,
) -> Dict:
    url = URL_LUMIR_RAG
    payload = {
        "question": question,
        "top_n": top_n,
        "score_threshold": score_threshold,
        "include_full_details": include_full_details,
        "collection_name": os.getenv("COLLECTION_RAG"),
    }
    response = requests.post(url, json=payload)
    return response.json()["contexts"]

