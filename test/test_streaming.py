#!/usr/bin/env python3
"""
Test streaming mode to check real-time response generation
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

# Load environment variables
load_dotenv()

from lumir_agentic.chat import ChatAgent

async def test_streaming():
    """Test streaming mode với câu hỏi cụ thể"""
    
    # Get configuration from environment
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
        
        # Stream response chunk by chunk
        full_response = ""
        async for chunk in agent.run_api(
            users_question=question,
            history=[],
            user_profile={"Name:": "Chaos "},
            language="english"
        ):
            print(chunk, end="", flush=True)
            full_response += chunk
        
        print("\n\n=== END STREAMING ===")
        print(f"\n✓ Total characters streamed: {len(full_response)}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Lỗi: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point"""
    success = asyncio.run(test_streaming())
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
