
import os
import sys
from typing import AsyncGenerator, Optional, Any, Dict
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Load environment variables
load_dotenv()

from lumir_agentic.core.agent.node import save_history, get_history
from lumir_agentic.chat import ChatAgent
from lumir_agentic.agent import AgentGraph
from lumir_agentic.core.agent.config import UserInfo

# Create FastAPI app
app = FastAPI(
    title="LUMIR Agentic API",
    description="API for LUMIR Agentic chat functionality",
    version="1.0.0"
)

class HistoryRequest(BaseModel):
    user_id: str
    session_id: str

class SaveHistoryRequest(BaseModel):
    user_id: str
    session_id: str
    user_message: str
    assistant_message: str

class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    question: str
    user_id: str
    user_name: str
    session_id: str
    language: str = "vietnamese"
    history: Optional[list] = None

class AgentRequest(BaseModel):
    question: str
    user_id: str
    session_id: str
    full_user_name: Optional[str] = None
    birthday: Optional[str] = None
    language: Optional[str] = "vietnamese"
    account_trading_id: str
    history: Optional[list] = None

class ChatResponse(BaseModel):
    """Response model for non-streaming chat endpoint"""
    response: str
    session_id: str
    user_id: str
    account_trading_id: Optional[str] = None

@app.post("/agent")
async def agent(request: AgentRequest):
    """
    Streaming chat endpoint that returns response in chunks

    Args:
        request: ChatRequest containing user info and question

    Returns:
        StreamingResponse with chat response chunks
    """

    model_name = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
    api_key = os.getenv("API_KEY")
    base_url = os.getenv("BASE_URL")

    if not api_key:
        raise HTTPException(status_code=500, detail="API_KEY not configured")


    # Create user info
    user_info = UserInfo(
        user_id=request.user_id,
        full_user_name=request.full_user_name,
        session_id=request.session_id,
        account_trading_id=request.account_trading_id,
        birthday=request.birthday
    )

    try:
        # Initialize Agent Graph
        print("Khởi tạo AgemtGraph...")
        agent = AgentGraph(
            model_name=model_name,
            api_key=api_key,    
            base_url=base_url,
            user_info=user_info,
        )
        print("✓ AgentGraph khởi tạo thành công\n")

        print(f"=== PROCESSING QUESTION: {request.question} ===\n")
        print("=== STREAMING RESPONSE (Agent) ===")

        # Stream response chunk by chunk
        full_response = ""
        async for chunk in agent.agent_response(
            user_question=request.question,
            history=request.history or [],
            user_profile={
                "full name": user_info.full_user_name,
                "user_id": user_info.user_id,
                "session_id": user_info.session_id,
                "birthday": user_info.birthday,
                "account_trading_id": user_info.account_trading_id,
            },
            language=request.language,
        ):
            if chunk:
                full_response += chunk

        return ChatResponse(
            response=full_response,
            session_id=request.session_id,
            user_id=request.user_id,
            account_trading_id=request.account_trading_id
        )

    except Exception as e:
        print(f"\n✗ Lỗi: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
   
@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Non-streaming chat endpoint that returns complete response

    Args:
        request: ChatRequest containing user info and question

    Returns:
        ChatResponse with complete response
    """

    # Get configuration from environment
    model_name = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
    api_key = os.getenv("API_KEY")
    base_url = os.getenv("BASE_URL")

    if not api_key:
        raise HTTPException(status_code=500, detail="API_KEY not configured")

    # Create user info
    user_info = UserInfo(
        user_id=request.user_id,
        full_user_name=request.user_name,
        session_id=request.session_id
    )

    try:
        # Initialize ChatAgent
        agent = ChatAgent(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            user_info=user_info
        )

        # Get complete response
        full_response = ""
        async for chunk in agent.chat_response(
            users_question=request.question,
            history=request.history or [],
            user_profile={
                "Name": request.user_name,
                "user_id": request.user_id,
                "session_id": request.session_id
            },
            language=request.language
        ):
            full_response += chunk

        return ChatResponse(
            response=full_response,
            session_id=request.session_id,
            user_id=request.user_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/history/get")
async def get_conversation_history(request: HistoryRequest):
    """Get conversation history for a user session"""
    try:
        history = await get_history(request.user_id, request.session_id)
        return {
            "success": True,
            "data": history,
            "message": f"Retrieved {len(history) if history else 0} conversation items"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")

@app.post("/history/save")
async def save_conversation_history(request: SaveHistoryRequest):
    """Save conversation messages to memory"""
    try:
        await save_history(
            request.user_id,
            request.session_id,
            request.user_message,
            request.assistant_message
        )
        return {
            "success": True,
            "message": "Conversation history saved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save history: {str(e)}")

def main():
    """Main function to run the API server"""
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=2026,
        reload=False
    )


if __name__ == "__main__":
    main()