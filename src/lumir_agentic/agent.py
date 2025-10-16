import json
import os
import requests
from typing import Dict, List, Any, Optional, AsyncGenerator
from .utils.logger import logger
from .core.agent.config import UserInfo

from .core.agent.prompt import (
    build_langchain_template,
    agent_generation_system_prompt)
from .core.agent.states import WorkflowAgentState, ReasoningStep
from .core.agent.node import reasoning_agent_node, use_tools, get_history
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from .core.agent.tools import (
    search_knowledge_base,
    get_mapping_keyword,
    calculate_tbi_indicators,
    format_live_trading_table,
    format_trade_account_table,
    format_trade_history_table,
    
)


class AgentGraph:

    def __init__(
        self,
        model_name: str,
        base_url: str,
        user_info: UserInfo,
    ):
        try:
            self.llm = ChatOpenAI(
                model_name=model_name,
                temperature=0,
                base_url=base_url,
            )
        except Exception as e:
            logger.error(f"Error initializing AgemtGraph: {e}")
            raise

        self.list_tools = [
            search_knowledge_base,
            get_mapping_keyword,
            calculate_tbi_indicators,
            format_live_trading_table,
            format_trade_account_table,
            format_trade_history_table,
        ]
        self.logger = logger
        self.user_info = user_info
        self.graph = self.create_graph()

    def create_graph(self) -> StateGraph:
        """Tạo StateGraph cho agent: reasoning → execute_tools (không generate)."""
        self.logger.info("Creating agent state graph (streaming, no generation node)...")
        workflow = StateGraph(WorkflowAgentState)

        # Các node của agent
        workflow.add_node("reasoning_step", self._reasoning_step_node)
        workflow.add_node("execute_tools", self._execute_tools_node)

        # Flow: reasoning -> execute -> END
        workflow.set_entry_point("reasoning_step")
        workflow.add_edge("reasoning_step", "execute_tools")
        workflow.add_edge("execute_tools", END)

        return workflow.compile()

    def get_memory_from_session(self , state: WorkflowAgentState) -> WorkflowAgentState:
        user_id  = self.user_info.user_id
        session_id = self.user_info.session_id
        if user_id and session_id:
            import asyncio
            try:
                if asyncio.iscoroutinefunction(get_history):
                        # If we're in an async context, use await
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Create a new task if loop is already running
                            task = asyncio.create_task(get_history(user_id, session_id))
                            memory_conversation = loop.run_until_complete(task)
                        else:
                            memory_conversation = loop.run_until_complete(get_history(user_id, session_id))
                    except RuntimeError:
                            # If no event loop, create one
                            memory_conversation = asyncio.run(get_history(user_id, session_id))
                else:
                    memory_conversation = get_history(user_id, session_id)
                
                state["conversation_history"] = memory_conversation
                self.logger.info(f"   Memory conversation loaded: {len(memory_conversation)} messages")
            except Exception as e:
                    self.logger.error(f"Error in get_history: {e}")
                    state["conversation_history"] = []
        return state

    def _reasoning_step_node(self, state: WorkflowAgentState) -> WorkflowAgentState:
        """Gọi reasoning_agent_node để tạo reasoning và log kết quả, đưa vào state."""
        try:
            # Get memory 
            try:
                self.get_memory_from_session(state)
                self.logger.info(f"   Conversation messages after get memory: {len(state.get('conversation_history', []))}")
            except Exception as e:
                self.logger.error(f"Error in get_memory_from_session: {e}")

            state["llm"] = state.get("llm") or self.llm
            state["user_info"] = state.get("user_info") or self.user_info

            self.logger.info("🧠 REASONING STEP:")
            self.logger.info(f"   User question: {state.get('user_question', '')}")
            self.logger.info(f"   Conversation messages: {len(state.get('conversation_history', []))}")
            response = reasoning_agent_node(state)
            reasoning_text = getattr(response, "content", "")
            
            if '"use_memory": false'  in reasoning_text:
                self.logger.info("   Not use memory")
                state["conversation_history"] = []

            state["reasoning"] = [
                ReasoningStep(step="reasoning_step", reasoning=reasoning_text)
            ]
            state["current_step"] = "execute_tools"

            self.logger.info(f"   Reasoning: {reasoning_text}")
            self.logger.info("   Next: execute_tools")
            return state
        except Exception as e:
            self.logger.error(f"Error in Reasoning Step Node: {e}")
            state["reasoning"] = [ReasoningStep(step="reasoning_step", reasoning=str(e))]
            state["current_step"] = "execute_tools"
            return state

    def _execute_tools_node(self, state: WorkflowAgentState) -> WorkflowAgentState:
        """Gọi use_tools để thực thi tool theo plan, lưu kết quả và log đầy đủ."""
        try:
            self.logger.info("🔧 EXECUTE TOOLS NODE:")

            state["llm"] = state.get("llm") or self.llm
            if not state.get("plan"):
                # Không dùng plan agent; dùng reasoning làm chỉ dẫn cho tools
                reasonings = state.get("reasoning", [])
                instruction = ""
                try:
                    parts = []
                    for r in reasonings:
                        if hasattr(r, "reasoning"):
                            parts.append(getattr(r, "reasoning", ""))
                        elif isinstance(r, dict):
                            parts.append(r.get("reasoning", ""))
                    instruction = "\n".join([p for p in parts if p])
                except Exception:
                    instruction = ""
                if not instruction:
                    instruction = state.get("user_question", "")
                state["plan"] = instruction
                self.logger.info("   Using reasoning as instruction for tools")

            # Đảm bảo list_tools
            state["list_tools"] = state.get("list_tools") or self.list_tools

            # Thực thi tools
            tool_results = use_tools(state)
            state["tools_called"] = tool_results
            return state
        except Exception as e:
            self.logger.error(f"Error in Execute Tools Node: {e}")
            state["tool_results"] = {"error": str(e)}
            state["tool_calls"] = []
            state["current_step"] = "response_generation"
            return state

    async def run_stream(
        self,
        user_question: str,
        # history: List[Dict[str, str]] = None,
        user_profile: Dict[str, Any] = None,
        language: str = "vietnamese",
    ) -> AsyncGenerator[str, None]:
        """Chạy agent ở chế độ streaming: thực thi graph, sau đó stream final LLM response."""
        # if history is None:
        #     history = []
        if user_profile is None:
            user_profile = {}

        self.logger.info(
            f"🚀 Running agent streaming with question: {user_question}"
        )

        try:
            conversation_history = []
            try:
                user_id = self.user_info.user_id
                session_id = self.user_info.session_id
                if user_id and session_id:
                    import asyncio
                    if asyncio.iscoroutinefunction(get_history):
                        conversation_history = await get_history(user_id, session_id)
                    else:
                        conversation_history = get_history(user_id, session_id)
                    self.logger.info(f"   Loaded conversation history: {len(conversation_history)} messages")
            except Exception as e:
                self.logger.error(f"Error loading history in run_stream: {e}")
                conversation_history = []
                
            initial_state: Dict[str, Any] = {
                "user_question": user_question,
                "conversation_history": conversation_history,
                "user_profile": user_profile,
                "current_step": "reasoning_step",
                "is_complete": False,
                "llm": self.llm,
                "memory_conversation": None,
                "language": language,
                "user_info": self.user_info,
            }

            # Chạy workflow (dừng sau execute_tools)
            self.logger.info("Running workflow (reasoning → execute_tools)...")
            final_state = None
            async for chunk in self.graph.astream(initial_state):
                node_name = list(chunk.keys())[0]
                node_output = chunk[node_name]
                final_state = node_output
                self.logger.info(f"   ✓ Node '{node_name}' completed")

            self.logger.info("Starting LLM streaming generation...")
            if final_state:
                user_question = final_state.get("user_question", "")
                conversation_history = final_state.get("conversation_history", [])
                tool_calls_result = final_state.get("tools_called", [])
                language_from_state = final_state.get("language", language)
                # self.logger.info(f"   Tool Calls Result: {tool_calls_result}")
                system_prompt = agent_generation_system_prompt(
                    tool_result=[tool_calls_result],
                    language=language_from_state,
                    user_profile=user_profile,
                )


                self.logger.info(f"   System Prompt: {system_prompt}")
                prompt = build_langchain_template(
                    user_input=user_question,
                    conversation_history=conversation_history,
                    system_prompt=system_prompt,
                )

                async for chunk in self.llm.astream(prompt):
                    if hasattr(chunk, "content") and chunk.content:
                        yield chunk.content
            else:
                yield "No response generated"

        except Exception as e:
            logger.error(f"Error in agent run_stream: {str(e)}")
            yield f"Error: {str(e)}"
        

