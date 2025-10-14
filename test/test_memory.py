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

from lumir_agentic.core.agent.memory import EncryptedMemoryManager
from lumir_agentic.core.agent.node import save_history, get_history
from lumir_agentic.chat import ChatAgent
from lumir_agentic.core.agent.config import UserInfo


async def test_streaming():
    """Test streaming mode với câu hỏi cụ thể"""
    
    # Get configuration from environment
    model_name = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
    api_key = os.getenv("API_KEY")
    base_url = os.getenv("BASE_URL")

    # Handle session and user info


    user_info = UserInfo(user_id= "test", full_user_name="Chaos", session_id="session_123")
    
    try:
        # Initialize ChatAgent
        print("Khởi tạo ChatAgent...")
        agent = ChatAgent(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            user_info=user_info
        )
        print("✓ ChatAgent khởi tạo thành công\n")

        question = " Chỉ số RI là Recommend Index phải không ? "
        print(f"=== TEST QUESTION: {question} ===\n")
        print("=== STREAMING RESPONSE ===")
        
        # Stream response chunk by chunk
        full_response = ""
        async for chunk in agent.run_stream(
            users_question=question,
            history=[],
            user_profile={"Name:": "Chaos ", "user_id": user_info.user_id, "session_id": user_info.session_id},
            language="vietnamese"
        ):
            print(chunk, end="", flush=True)
            full_response += chunk
        
        print("\n\n=== END STREAMING ===")
        print(f"\n✓ Total characters streamed: {len(full_response)}")

        try:
            # Save conversation history
            await save_history(user_info.user_id, user_info.session_id, user_message=question, assistant_message=full_response)
            print("✓ Conversation history saved successfully")
        except Exception as e:
            # create new session and retry

            print(f"\n✗ Lỗi: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
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
