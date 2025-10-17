
#!/usr/bin/env python3
"""
Test streaming mode for AgemtGraph to verify end-to-end flow
including tool execution and saving conversation to encrypted memory.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

# Load environment variables
load_dotenv()

# Ensure OPENAI_API_KEY is set for ChatOpenAI
api_key_env = os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
if api_key_env and not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = api_key_env

from lumir_agentic.agent import AgentGraph
from lumir_agentic.core.agent.node import save_history
from lumir_agentic.core.agent.config import UserInfo


async def test_streaming_agent():
    """Test streaming mode với AgemtGraph và lưu lịch sử hội thoại"""

    # Get configuration from environment
    model_name = os.getenv("MODEL_NAME", "gpt-4.1-nano-2025-04-14")
    base_url = os.getenv("BASE_URL")

    # Prepare user info
    user_info = UserInfo(
        full_user_name="Nguyễn Nhật Trường",
        user_id="1709",
        session_id="session_agent_123",
        birthday="20/02/2003",
        account_trading_id="272515048",
    )

    try:
        # Initialize Agent Graph
        print("Khởi tạo AgemtGraph...")
        agent = AgentGraph(
            model_name=model_name,
            base_url=base_url,
            user_info=user_info,
        )
        print("✓ AgemtGraph khởi tạo thành công\n")

        # question = " Tôi vừa hỏi bạn điều gì vậy ?  "
        question = " Hãy phân tích lịch sử trade của tôi :"
        print(f"=== TEST QUESTION: {question} ===\n")
        print("=== STREAMING RESPONSE (Agent) ===")

        # Stream response chunk by chunk
        full_response = ""
        async for chunk in agent.run_stream(
            user_question=question,
            # history=[],
            user_profile={
                "full name": user_info.full_user_name,
                "user_id": user_info.user_id,
                "session_id": user_info.session_id,
                "birthday": user_info.birthday,
                "account_trading_id": user_info.account_trading_id,
            },
            language="vietnamese",
        ):
            if chunk:
                full_response += chunk

        print("\n\n=== END STREAMING ===")
        print(f"\n✓ Total characters streamed: {len(full_response)}")

        try:
            # Save conversation history
            await save_history(user_info.user_id, user_info.session_id, user_message=question, assistant_message=full_response)
            print("✓ Conversation history saved successfully (agent)")
            return True
        except Exception as e:
            print(f"\n✗ Lỗi lưu lịch sử: {str(e)}")
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
    success = asyncio.run(test_streaming_agent())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()