import json
import os
from typing import Dict , List , Any , Optional, AsyncGenerator
from .utils.logger import logger
from .core.agent.prompt import render_prompt
from .core.agent.states import WorkflowAgentState, WorkflowChatState, ReasoningStep, ToolCall, Plan, UseMemory
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from .core.agent.prompt import (
    memory_decision_prompt,
    reasoning_prompt,
    chat_generation_prompt,
)

from .core.agent.tools import (
    search_knowledge_base,
    get_mapping_keyword,
    get_memory_context,
)

# Add missing analyze_user_question_prompt function
def analyze_user_question_prompt(user_question: str, conversation_history: str = "", user_profile: dict = None) -> str:
    """Analyze user question prompt - dummy implementation for testing"""
    return reasoning_prompt(user_question, conversation_history, user_profile)


class ChatAgent:

    """A chat agent that uses a language model to interact with users and perform tasks.
    Attributes:
        llm: The language model used by the agent.
        tools: A list of tools that the agent can use to perform tasks.
        system_message: The system message that sets the context for the conversation.
        chat_history: A list of messages representing the chat history.
        state: The current state of the agent, including memory and workflow information.
    """

    def __init__(self, model_name:str , 
                 api_key:str , 
                 tools:List[ToolNode] = None, 
                 system_message:Optional[str]=None,
                 base_url: str = None):
        
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
        self.graph = self._create_graph()
        self.graph_without_generation = self._create_graph_without_generation()
        
    def _create_graph(self) -> StateGraph:

        self.logger.info("Creating state graph...")
        workflow = StateGraph(WorkflowChatState)

        # Add nodes with proper node functions
        workflow.add_node("memory_decision", self._memory_decision_node)
        workflow.add_node("analyze_user_question", self._analyze_user_question_node)
        workflow.add_node("use_memory", self._use_memory_node)
        workflow.add_node("search_rag", self._search_rag_node)
        workflow.add_node("execute_tools", self._execute_tools_node)
        workflow.add_node("generate_response", self._generate_response_node)

        # Add edges
        workflow.set_entry_point("memory_decision")
        workflow.add_conditional_edges(
            "memory_decision",
            lambda x: "use_memory" if x.get("use_memory", False) else "analyze_user_question"
        )
        workflow.add_edge("use_memory", "analyze_user_question")
        workflow.add_edge("analyze_user_question", "search_rag")
        workflow.add_edge("search_rag", "generate_response")
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
        workflow.add_node("search_rag", self._search_rag_node)
        workflow.add_node("execute_tools", self._execute_tools_node)

        # Add edges - stop at search_rag (no generation)
        workflow.set_entry_point("memory_decision")
        workflow.add_conditional_edges(
            "memory_decision",
            lambda x: "use_memory" if x.get("use_memory", False) else "analyze_user_question"
        )
        workflow.add_edge("use_memory", "analyze_user_question")
        workflow.add_edge("analyze_user_question", "search_rag")
        workflow.add_edge("search_rag", END)  # Stop here, no generation

        return workflow.compile()

    def _memory_decision_node(self, state: WorkflowChatState) -> WorkflowChatState:
        """Decide if memory is needed"""
        try:
            user_question = state.get("user_question", "")
            memory_conversation = state.get("memory_conversation")
            
            self.logger.info(f"🔍 MEMORY DECISION NODE:")
            self.logger.info(f"   Input: {user_question}")
            
            # Use LLM to make memory decision
            prompt = memory_decision_prompt(
                user_question=user_question, 
                memory_conversation=memory_conversation
            )
            
            response = self.llm.invoke(prompt)
            decision_text = response.content.strip().lower()
            
            # Parse the decision
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
        """Analyze user question"""
        try:
            user_question = state.get("user_question", "")
            conversation_history = state.get("conversation_history", [])
            user_profile = state.get("user_profile", {})
            
            # Simple analysis for testing
            analysis_result = f"Analyzed question: {user_question}"
            state["analysis_result"] = analysis_result
            state["current_step"] = "search_rag"
            
            self.logger.info(f"📝 ANALYZE USER QUESTION NODE:")
            self.logger.info(f"   Input: {user_question}")
            self.logger.info(f"   Analysis: {analysis_result}")
            self.logger.info(f"   Next: search_rag")
            return state
        except Exception as e:
            self.logger.error(f"Error in Analyze User Question Node: {e}")
            return state

    def _use_memory_node(self, state: WorkflowChatState) -> WorkflowChatState:
        """Use memory context - dummy implementation"""
        try:
            user_question = state.get("user_question", "")
            
            self.logger.info(f"💾 USE MEMORY NODE:")
            self.logger.info(f"   Input: {user_question}")
            self.logger.info(f"   Use Memory: {state.get('use_memory', False)}") # Log the use_memory state
            
            # Retrieve actual memory context
            state["memory_context"] = get_memory_context(state)
            self.logger.info(f"   Output: Memory context retrieved")
            state["current_step"] = "analyze_user_question"
            
            self.logger.info(f"   Output: Dummy memory context retrieved")
            self.logger.info(f"   Next: analyze_user_question")
            
            return state
        except Exception as e:
            self.logger.error(f"Error in Use Memory Node: {e}")
            return state

    def _execute_tools_node(self, state: WorkflowChatState) -> WorkflowChatState:
        """Execute tools"""
        try:
            self.logger.info(f"🔧 EXECUTE TOOLS NODE:")
            self.logger.info(f"   Input: Tool execution requested")
            
            # Simple tool execution for testing
            state["tool_results"] = "Tool execution completed (dummy)"
            state["current_step"] = "generate_response"
            
            self.logger.info(f"   Output: Tool execution completed (dummy)")
            self.logger.info(f"   Next: generate_response")
            
            return state
        except Exception as e:
            self.logger.error(f"Error in Execute Tools Node: {e}")
            return state

    def _search_rag_node(self, state: WorkflowChatState) -> WorkflowChatState:
        try:
            user_question = state.get("user_question", "")
            
            self.logger.info(f"🔍 SEARCH RAG NODE:")
            self.logger.info(f"   Input: {user_question}")
            
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
            prompt = chat_generation_prompt(
                user_question=user_question,
                conversation_history=str(conversation_history),
                tool_results=[tc.result for tc in tool_calls],
                language=state.get("language")
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

    async def _generate_response_stream(self, users_question:str,
                                        history:List[Dict[str,str]],
                                        tool_calls:List[ToolCall],
                                        ) -> AsyncGenerator:
        """Generate a response stream for the given user question and chat history.
        Args:
            users_question: The user's question.
            history: The chat history, a list of dictionaries with "role" and "content" keys.
        Returns:
            The generated response stream.
        """

        prompt = render_prompt(
            template_name='chat',
            user_question = users_question,
            conversation_history = history,
            tool_calls = tool_calls,
        )
        
        # Stream response from LLM
        async for chunk in self.llm.astream(prompt):
            if hasattr(chunk, 'content'):
                yield chunk.content

    async def run_stream(self, users_question: str,
                         history: List[Dict[str, str]] = None,
                         tool_calls: List[ToolCall] = None,
                         user_profile: Dict[str, str] = None,
                         language: str = "vietnamese"
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
                conversation_history = final_state.get("conversation_history", [])
                tool_calls_result = final_state.get("tool_calls", [])
                language_from_state = final_state.get("language", language)
                
                # Build prompt same as _generate_response_node
                prompt = chat_generation_prompt(
                    user_question=user_question,
                    conversation_history=str(conversation_history),
                    tool_results=[tc.result for tc in tool_calls_result],
                    language=language_from_state
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
        



        
