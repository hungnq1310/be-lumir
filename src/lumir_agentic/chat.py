import json
import os
import requests
from typing import Dict , List , Any , Optional, AsyncGenerator
from .utils.logger import logger
from .core.agent.config import UserInfo

from .core.agent.prompt import chat_generation_system_prompt, build_langchain_template
from .core.agent.states import WorkflowAgentState, WorkflowChatState, ReasoningStep, ToolCall, Plan, UseMemory
from .core.agent.node import get_history, save_history
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from .core.agent.prompt import (
    memory_decision_prompt,
    chat_generation_system_prompt,
)

from .core.agent.tools import (
    search_knowledge_base,
    get_mapping_keyword,
    get_memory_context,
)



class ChatAgent:

    """A chat agent that uses a language model to interact with users and perform tasks.
    Attributes:
        llm: The language model used by the agent.
        tools: A list of tools that the agent can use to perform tasks.
        chat_history: A list of messages representing the chat history.
        state: The current state of the agent, including memory and workflow information.
    """

    def __init__(self, model_name:str , 
                 api_key:str , 
                 base_url: str = None,
                 user_info:UserInfo = None):
        
        if base_url:
            self.llm = ChatOpenAI(
                model_name=model_name, 
                openai_api_key=api_key, 
                temperature=0,
                base_url=base_url
            )
        else:
            self.llm = ChatOpenAI(model_name=model_name , openai_api_key=api_key , temperature=0)
            
        self.tools = {
                "search_knowledge_base": search_knowledge_base
                ,"get_mapping_keyword": get_mapping_keyword
                ,"get_memory_context": get_memory_context
            }
        
        self.logger = logger
        self.user_info = user_info
        self.graph = self._create_graph()
        self.graph_without_generation = self._create_graph_without_generation()
        
    def _create_graph(self) -> StateGraph:
        self.logger.info("Creating state graph...")
        workflow = StateGraph(WorkflowChatState)
        # Add nodes with proper node functions
        workflow.add_node("memory_decision", self._memory_decision_node)
        workflow.add_node("analyze_user_question", self._analyze_user_question_node)
        workflow.add_node("use_memory", self._use_memory_node)
        workflow.add_node("search_info", self._search_info_node)
        workflow.add_node("execute_tools", self._execute_tools_node)
        workflow.add_node("generate_response", self._generate_response_node)

        # Add edges
        workflow.set_entry_point("memory_decision")
        workflow.add_conditional_edges(
            "memory_decision",
            lambda x: "use_memory" if x.get("use_memory", False) else "analyze_user_question"
        )
        workflow.add_edge("use_memory", "analyze_user_question")
        workflow.add_edge("analyze_user_question", "search_info")
        workflow.add_edge("search_info", "execute_tools")
        workflow.add_edge("execute_tools", "generate_response")
        workflow.add_edge("generate_response", END)

        return workflow.compile()
    
    def _create_graph_without_generation(self) -> StateGraph:
        """Create graph without final generation node - for streaming mode"""
        self.logger.info("Creating state graph without generation node (for streaming)...")
        workflow = StateGraph(WorkflowChatState)
        # Add nodes - same as normal graph but WITHOUT generate_response
        workflow.add_node("memory_decision", self._memory_decision_node)
        workflow.add_node("analyze_user_question", self._analyze_user_question_node)
        workflow.add_node("use_memory", self._use_memory_node)
        workflow.add_node("search_info", self._search_info_node)
        workflow.add_node("execute_tools", self._execute_tools_node)
        workflow.set_entry_point("memory_decision")
        workflow.add_conditional_edges(
            "memory_decision",
            lambda x: "use_memory" if x.get("use_memory", False) else "analyze_user_question"
        )
        workflow.add_edge("use_memory", "analyze_user_question")
        workflow.add_edge("analyze_user_question", "search_info")
        workflow.add_edge("search_info", "execute_tools")
        workflow.add_edge("execute_tools", END)  # Stop here, no generation

        return workflow.compile()

    def _memory_decision_node(self, state: WorkflowChatState) -> WorkflowChatState:
        """Decide if memory is needed"""
        try:
            user_question = state.get("user_question", "")
            user_profile = state.get("user_profile", {})
            memory_conversation = state.get("memory_conversation")
            
            self.logger.info(f"🔍 MEMORY DECISION NODE:")
            self.logger.info(f"   Input: {user_question}")
            
            # Load conversation history from memory if user_id and session_id are available
            user_id = user_profile.get("user_id")
            session_id = user_profile.get("session_id")
            
            self.logger.info(f"   User profile: {user_profile}")
            if user_id and session_id:
                # Load conversation history from encrypted memory
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
                    
                    state["memory_conversation"] = memory_conversation
                    self.logger.info(f"   Using user_id: {user_id}, session_id: {session_id}")
                except Exception as e:
                    self.logger.error(f"   Error loading memory: {e}")
                    memory_conversation = None
            
            # Use LLM to make memory decision
            prompt = memory_decision_prompt(
                user_question=user_question, 
                memory_conversation=memory_conversation
            )
            
            response = self.llm.invoke(prompt)
            decision_text = response.content.strip().lower()
            
            # Parse the decision
            print(f"Decision text: {decision_text}")
            # quit()
            use_memory = decision_text == "true"
            state["use_memory"] = use_memory
            state["current_step"] = "use_memory" if use_memory else "analyze_user_question"
            
            decision_msg = "needed" if use_memory else "no_needed"
            next_step = "use_memory" if use_memory else "analyze_user_question"
            
            self.logger.info(f"   Decision: {decision_msg}")
            self.logger.info(f"   Next: {next_step}")
            
            return state
        except Exception as e:
            self.logger.error(f"Error in Memory Decision Node: {e}")
            state["use_memory"] = False
            state["current_step"] = "analyze_user_question"
            return state

    def _analyze_user_question_node(self, state: WorkflowChatState) -> WorkflowChatState:
        """Analyze user question using chat_plan from node.py"""
        try:
            from .core.agent.node import chat_plan
            
            user_question = state.get("user_question", "")
            conversation_history = state.get("conversation_history", [])
            
            self.logger.info(f"📝 ANALYZE USER QUESTION NODE:")
            self.logger.info(f"   Input: {user_question}")
            
            # Set LLM in state for chat_plan to use
            state["llm"] = self.llm
            
            # Use chat_plan to generate a plan
            plan = chat_plan(state, conversation_history, user_question)
            
            state["plan"] = plan
            state["analysis_result"] = f"Plan generated: {plan[:100]}..." if len(plan) > 100 else plan
            state["current_step"] = "search_info"
            
            self.logger.info(f"   Plan: {plan}..." )
            self.logger.info(f"   Next: search_info")
            return state
        except Exception as e:
            self.logger.error(f"Error in Analyze User Question Node: {e}")
            # Fallback to simple analysis if chat_plan fails
            state["analysis_result"] = f"Analyzed question: {user_question}"
            state["current_step"] = "search_info"
            return state

    def _use_memory_node(self, state: WorkflowChatState) -> WorkflowChatState:
        """Use memory context"""
        try:
            user_question = state.get("user_question", "")
            memory_conversation = state.get("memory_conversation", [])
            
            self.logger.info(f"💾 USE MEMORY NODE:")
            self.logger.info(f"   Input: {user_question}")
            self.logger.info(f"   Use Memory: {state.get('use_memory', False)}")
            self.logger.info(f"   Memory Messages: {len(memory_conversation) if memory_conversation else 0}")
            
            # Use the loaded memory conversation as context
            if memory_conversation:
                # Format memory conversation for context
                memory_context = []
                for msg in memory_conversation:
                    if isinstance(msg, dict):
                        role = msg.get('role', 'user')
                        content = msg.get('content', '')
                        memory_context.append(f"{role}: {content}")
                    else:
                        memory_context.append(str(msg))
                
                state["memory_context"] = "\n".join(memory_context)
                self.logger.info(f"   Memory Context: {len(state['memory_context'])} characters")
            else:
                state["memory_context"] = ""
                self.logger.info(f"   Memory Context: Empty")
            
            state["current_step"] = "analyze_user_question"
            self.logger.info(f"   Next: analyze_user_question")
            
            return state
        except Exception as e:
            self.logger.error(f"Error in Use Memory Node: {e}")
            state["memory_context"] = ""
            state["current_step"] = "analyze_user_question"
            return state

    def _execute_tools_node(self, state: WorkflowChatState) -> WorkflowChatState:
        """Execute tools using use_tools from node.py"""
        try:
            from .core.agent.node import use_tools
            from .core.agent.tools import search_knowledge_base, get_mapping_keyword, get_memory_context
            
            self.logger.info(f"🔧 EXECUTE TOOLS NODE:")
            self.logger.info(f"   Input: Tool execution requested")
            
            # Ensure LLM is in state
            if "llm" not in state:
                state["llm"] = self.llm
            
            # Ensure plan is in state
            elif "plan" not in state:
                self.logger.warning("No plan found in state, using default plan")
                user_question = state.get("user_question", "")
                state["plan"] = f"Search for information about: {user_question}"
            
            # Set available tools
            state["list_tools"] = [
                search_knowledge_base,
                get_mapping_keyword,
                get_memory_context
            ]
            
            # Execute tools using use_tools
            tool_results = use_tools(state)
            
            # Store results in state
            state["tool_results"] = tool_results
            
            # Convert tool_results to ToolCall objects for compatibility
            tool_calls = []
            for tool_name, result in tool_results.items():
                tool_call = ToolCall(
                    tool_name=tool_name,
                    parameters={},  
                    result=str(result),
                    success=not str(result).startswith("❌")
                )
                tool_calls.append(tool_call)
            
            state["tool_calls"] = tool_calls
            state["current_step"] = "generate_response"
            
            self.logger.info(f"   Output: {len(tool_calls)} tools executed")
            self.logger.info(f"   Next: generate_response")
            
            return state
        except Exception as e:
            self.logger.error(f"Error in Execute Tools Node: {e}")
            # Fallback to dummy implementation
            state["tool_results"] = f"Tool execution error: {str(e)}"
            state["tool_calls"] = []
            state["current_step"] = "generate_response"
            return state

    def _search_info_node(self, state: WorkflowChatState) -> WorkflowChatState:
        """Search info node - now redirects to execute_tools_node if plan exists"""
        try:
            user_question = state.get("user_question", "")
            
            self.logger.info(f"🔍 SEARCH INFO NODE:")
            self.logger.info(f"   Input: {user_question}")
        
            
            # If we have a plan from analyze_user_question_node, do NOT call execute_tools here
            # Let the graph transition (search_info -> execute_tools) handle it to avoid double execution
            if state.get("plan"):
                self.logger.info(f"   Plan exists, proceeding to execute_tools via graph edge")
                state["current_step"] = "execute_tools"
                return state
            
            # Otherwise, use the original implementation
            result = search_knowledge_base.invoke({"question": user_question})
            
            if isinstance(result, dict) and result.get("success"):
                search_data = result.get("data", [])
                if search_data:
                    formatted_result = f"Found {len(search_data)} results:\n\n"
                    for i, item in enumerate(search_data[:5], 1):
                        if isinstance(item, dict):
                            content = item.get("content", item.get("text", str(item)))
                            formatted_result += f"{i}. {content}\n\n"
                        else:
                            formatted_result += f"{i}. {str(item)}\n\n"
                    result_string = formatted_result.strip()
                else:
                    result_string = "No relevant information found in knowledge base."
            else:
                result_string = result.get("message", "Unknown error during search.")
            
            tool_call = ToolCall(
                tool_name="search_knowledge_base",
                parameters={"question": user_question},
                result=result_string,
                success=True
            )
            
            state["tool_calls"] = [tool_call]
            state["current_step"] = "generate_response"
            
            self.logger.info(f"   Search Results: {len(search_data) if 'search_data' in locals() else 0} items found")
            self.logger.info(f"   Output: {result_string}")
            self.logger.info(f"   Next: generate_response")
            
        except Exception as e:
            self.logger.error(f"Error in RAG search: {str(e)}")
            user_question = state.get("user_question", "")
            tool_call = ToolCall(
                tool_name="search_knowledge_base",
                parameters={"question": user_question},
                result=f"Search error: {str(e)}",
                success=False
            )
            state["tool_calls"] = [tool_call]
            state["current_step"] = "generate_response"
            
        return state

    def _generate_response_node(self, state: WorkflowChatState) -> WorkflowChatState:
        """Generate final response"""
        try:
            user_question = state.get("user_question", "")
            conversation_history = state.get("conversation_history", [])
            tool_calls = state.get("tool_calls", [])
            
            self.logger.info(f"🤖 GENERATE RESPONSE NODE:")
            self.logger.info(f"   Input Question: {user_question}")
            self.logger.info(f"   Tool Results: {len(tool_calls)} tools executed")
            
            # Generate response using LLM
            memory_context = state.get("memory_context", "")
            system_prompt = chat_generation_system_prompt(
                # user_question=user_question,
                # conversation_history=str(conversation_history),
                user_profile=state.get("user_profile", ""),
                tool_results=[tc.result for tc in tool_calls],
                language=state.get("language")
            )

            prompt = build_langchain_template(
                user_input=user_question,
                conversation_history=conversation_history,
                system_prompt=system_prompt,
            )
            
            response = self.llm.invoke(prompt)
            state["final_response"] = response.content
            state["is_complete"] = True
            
            self.logger.info(f"   Generated Response: {response.content}")
            self.logger.info(f"   Status: Complete")
            
            return state
        except Exception as e:
            self.logger.error(f"Error in Generate Response Node: {e}")
            state["final_response"] = f"Error generating response: {str(e)}"
            state["is_complete"] = True
            return state

    async def run_stream(self, users_question: str,
                         history: List[Dict[str, str]] = None,
                         tool_calls: List[ToolCall] = None,
                         user_profile: Dict[str, str] = None,
                         language: str = "vietnamese",
                         ) -> AsyncGenerator:
        """Run the chat agent in streaming mode - same workflow as run_sync but streams final LLM response"""
        
        if history is None:
            history = []
        if tool_calls is None:
            tool_calls = []
        if user_profile is None:
            user_profile = {}
            
        self.logger.info(f"🚀 Running chat agent in streaming mode with question: {users_question}")
        
        try:
            initial_state = {
                "user_question": users_question,
                "conversation_history": history,
                "tool_calls": tool_calls,
                "user_profile": user_profile,
                "current_step": "memory_decision",
                "is_complete": False,
                "llm": self.llm,
                "memory_conversation": None,
                "language": language,
            }

            # Run workflow WITHOUT generation node (stop at search_rag)
            self.logger.info("Running workflow (memory → analyze → search_rag)...")
            final_state = None
            async for chunk in self.graph_without_generation.astream(initial_state):
                node_name = list(chunk.keys())[0]
                node_output = chunk[node_name]
                final_state = node_output
                self.logger.info(f"   ✓ Node '{node_name}' completed")
            
            # Now we have final_state with all data - stream the final LLM generation
            self.logger.info("Starting LLM streaming generation...")
            if final_state:
                user_question = final_state.get("user_question", "")
                conversation_history = final_state.get("memory_conversation", [])
                # conversation_history = conversation_history[-top_conversations:]
                # memory_context = final_state.get("memory_context", "")
                tool_calls_result = final_state.get("tool_calls", [])
                language_from_state = final_state.get("language", language)
                
                # Build prompt same as _generate_response_node
                system_prompt = chat_generation_system_prompt(
                    # user_question=user_question,
                    # conversation_history=str(conversation_history),
                    tool_results=[tc.result for tc in tool_calls_result],
                    language=language_from_state,
                    user_profile=user_profile,
                    # memory_context=memory_context
                )

                prompt = build_langchain_template(
                    user_input=user_question,
                    conversation_history=conversation_history,
                    system_prompt=system_prompt,
                )
                
                # Stream response from LLM chunk by chunk (ONLY difference from sync)
                async for chunk in self.llm.astream(prompt):
                    if hasattr(chunk, 'content') and chunk.content:
                        yield chunk.content
            else:
                yield "No response generated"
                        
        except Exception as e:
            logger.error(f"Error in run_stream: {str(e)}")
            yield f"Error: {str(e)}"

    def run_sync(self, users_question: str,
                 history: List[Dict[str, str]] = None,
                 tool_calls: List[ToolCall] = None,
                 user_profile: Dict[str, str] = None,
                 language: str = "vietnamese") -> str:
        """Run the chat agent synchronously"""
        
        if history is None:
            history = []
        if tool_calls is None:
            tool_calls = []
        if user_profile is None:
            user_profile = {}
            
        self.logger.info(f"🚀 Running chat agent synchronously with question: {users_question}")
        
        try:
            initial_state = {
                "user_question": users_question,
                "conversation_history": history,
                "tool_calls": tool_calls,
                "user_profile": user_profile,
                "current_step": "memory_decision",
                "is_complete": False,
                "llm": self.llm,
                "memory_conversation": None,
                "language": language,
            }

            final_state = self.graph.invoke(initial_state)
            
            if final_state and final_state.get("final_response"):
                return final_state["final_response"]
            else:
                return "No response generated"
                
        except Exception as e:
            logger.error(f"Error in run_sync: {str(e)}")
            return f"Error: {str(e)}"
    
    def streaming_api(self,session_id: str = "",
        model: str = os.getenv("STREAMING_MODEL", "gpt-4.1-nano-2025-04-14"),
        messages: List[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
        top_p: float = 1.0,
        stream: bool = True,
        url: str = os.getenv("STREAMING_URL", "https://beproto.pythera.ai/windmill/stream-llm"),
        timeout: int = 100
        ):
        payload = {
            "session_id": session_id,
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": stream,
        }

        # Headers
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        self.logger.info(f"🚀 Sending request to: {url}")
        self.logger.info(f"📝 Model: {model}")
        self.logger.info(f"🔧 Session ID: {session_id}")
        self.logger.info(
            f"📊 Parameters: temperature={temperature}, max_tokens={max_tokens}, top_p={top_p}"
        )
        self.logger.info(f"💬 Số lượng messages: {len(messages)}")
        self.logger.info("-" * 50)

        try:
            response = requests.post(url, json=payload, timeout=timeout)

            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"❌ Request failed: {e}")
            return None
    
    async def chat_response(self, users_question: str,
                         history: List[Dict[str, str]] = None,
                         tool_calls: List[ToolCall] = None,
                         user_profile: Dict[str, str] = None,
                         language: str = "vietnamese",
                        #  top_conversations: int = 5
                         ):
        """Run the chat agent in streaming mode - same workflow as run_sync but streams final LLM response"""
        
        if history is None:
            history = []
        if tool_calls is None:
            tool_calls = []
        if user_profile is None:
            user_profile = {}
            
        self.logger.info(f"🚀 Running chat agent in streaming mode with question: {users_question}")
        
        try:
            initial_state = {
                "user_question": users_question,
                "conversation_history": history,
                "tool_calls": tool_calls,
                "user_profile": user_profile,
                "current_step": "memory_decision",
                "is_complete": False,
                "llm": self.llm,
                "memory_conversation": None,
                "language": language,
            }

            # Run workflow WITHOUT generation node (stop at search_rag)
            self.logger.info("Running workflow (memory → analyze → search_rag)...")
            final_state = None
            async for chunk in self.graph_without_generation.astream(initial_state):
                node_name = list(chunk.keys())[0]
                node_output = chunk[node_name]
                final_state = node_output
                self.logger.info(f"   ✓ Node '{node_name}' completed")
            
            
            # Now we have final_state with all data - stream the final LLM generation
            self.logger.info("Starting LLM streaming generation...")
            if final_state:
                user_question = final_state.get("user_question", "")
                conversation_history = final_state.get("memory_conversation", [])
                
                tool_calls_result = final_state.get("tool_calls", [])
                language_from_state = final_state.get("language", language)
                
                # Build prompt same as _generate_response_node
                system_prompt = chat_generation_system_prompt(
                    tool_results=[tc.result for tc in tool_calls_result],
                    language=language_from_state,
                    user_profile=user_profile,
                )
                # Create conversation with system prompt
                conversation = [
                    {"role":"system","content":system_prompt},
                ]
                conversation.extend(conversation_history)
                # Add user question
                conversation.append({"role":"user","content":user_question})
                response = self.streaming_api(messages = conversation)
                yield response['result']['content']

            else:
                yield "No response generated"
                        
        except Exception as e:
            logger.error(f"Error in run_api: {str(e)}")
            yield f"Error: {str(e)}"
