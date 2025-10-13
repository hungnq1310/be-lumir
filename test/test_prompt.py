from src.lumir_agentic.chat import ChatAgent
import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv()

model_name = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")
    
try:
    # Initialize ChatAgent
    print("Khởi tạo ChatAgent...")
    agent = ChatAgent(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url
    )
    print("✓ ChatAgent khởi tạo thành công\n")
    
    # Test với câu hỏi cụ thể
    question = "Hi ?"
    print(f"=== TEST QUESTION: {question} ===\n")
    print("=== STREAMING RESPONSE ===")
    prompt = agent.get_prompt()
    
except Exception as e:
    print(e)
