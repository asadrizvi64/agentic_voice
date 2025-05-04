#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Orchestration Agent
----------------
Responsible for coordinating the interactions between agents and managing the registration workflow.
"""

import langgraph.graph as lg
from langgraph.graph import END, StateGraph
from enum import Enum
from typing import Dict, List, Any, TypedDict, Literal

# Import Ollama using the new import path
from langchain_ollama import OllamaLLM

from agents.perception_agent import PerceptionAgent
from agents.memory_agent import MemoryAgent
from agents.action_agent import ActionAgent

# Define registration states
class RegistrationStatus(str, Enum):
    INITIALIZED = "initialized"
    GATHERING_INFO = "gathering_info"
    PASSWORD_NEEDED = "password_needed"
    CONFIRMING = "confirming"
    COMPLETED = "completed"
    FAILED = "failed"

# Define state type
class RegistrationState(TypedDict):
    """State for the registration process."""
    session_id: str
    user_profile: Dict[str, Any]
    status: RegistrationStatus
    missing_fields: List[str]
    password: str
    current_message: str
    system_message: str

class OrchestrationAgent:
    """Agent responsible for coordinating the multi-agent system."""
    
    def __init__(self, base_url="http://localhost:11434", model="llama3"):
        """
        Initialize the orchestration agent.
        
        Args:
            base_url: Ollama API base URL
            model: LLM model to use
        """
        # Initialize Ollama with new import
        ollama_llm = OllamaLLM(
            model=model,
            base_url=base_url
        )
        
        # Initialize agents
        self.memory_agent = MemoryAgent()
        self.perception_agent = PerceptionAgent(llm=ollama_llm)
        self.action_agent = ActionAgent(self.memory_agent)
        
        # Session storage
        self.sessions = {}
        
        # Build the workflow graph
        self.graph = self._build_registration_graph()
    
    def _build_registration_graph(self):
        """Build a simplified graph for the registration workflow that avoids recursion"""
        # Create the graph
        builder = StateGraph(RegistrationState)
        
        # Add nodes with clearly defined responsibilities
        builder.add_node("process_message", self._process_message_node)
        builder.add_node("update_user_profile", self._update_user_profile)
        builder.add_node("check_registration_status", self._check_registration_status)
        builder.add_node("handle_registration", self._handle_registration)
        builder.add_node("generate_response", self._generate_response)
        
        # Define a clear, non-recursive flow
        builder.add_edge("process_message", "update_user_profile")
        builder.add_edge("update_user_profile", "check_registration_status")
        
        # Conditional edge: either register user or generate response
        builder.add_conditional_edges(
            "check_registration_status",
            self._should_register_conditional,
            {
                "handle_registration": "handle_registration",
                "generate_response": "generate_response"
            }
        )
        
        # Continue to response generation after registration
        builder.add_edge("handle_registration", "generate_response")
        
        # All paths end after response generation
        builder.add_edge("generate_response", END)
        
        # Set entry point
        builder.set_entry_point("process_message")
        
        # Compile with higher recursion limit as a safety measure
        return builder.compile(recursion_limit=50)
    
    def _process_message_node(self, state: RegistrationState) -> RegistrationState:
        """First node: Process the incoming message"""
        # Use perception agent to extract entities and intent
        perception_result = self.perception_agent.process_input(state["current_message"])
        
        # Store the perception result for use in later nodes
        state["perception_result"] = perception_result
        
        return state
    
    def _update_user_profile(self, state: RegistrationState) -> RegistrationState:
        """Second node: Update the user profile with extracted entities"""
        perception_result = state.get("perception_result", {})
        entities = perception_result.get("entities", {})
        
        # Update user profile with extracted entities
        for key, value in entities.items():
            if key == "password":
                state["password"] = value
            else:
                state["user_profile"][key] = value
        
        return state
    
    def _check_registration_status(self, state: RegistrationState) -> RegistrationState:
        """Third node: Check registration status and determine what's next"""
        # Check for missing fields
        result = self.action_agent.verify_profile_completeness(state["user_profile"])
        state["missing_fields"] = result.get("missing_fields", [])
        
        # Update status based on the result
        if result["status"] == "complete":
            if not state["password"]:
                state["status"] = RegistrationStatus.PASSWORD_NEEDED
            elif "yes" in state["current_message"].lower() or "correct" in state["current_message"].lower():
                state["status"] = RegistrationStatus.CONFIRMING
            else:
                state["status"] = RegistrationStatus.CONFIRMING
        else:
            state["status"] = RegistrationStatus.GATHERING_INFO
        
        return state
    
    def _should_register_conditional(self, state: RegistrationState) -> str:
        """Conditional logic to determine if we should register the user"""
        if (state["status"] == RegistrationStatus.CONFIRMING and 
            len(state["missing_fields"]) == 0 and 
            state["password"] and
            ("yes" in state["current_message"].lower() or "correct" in state["current_message"].lower())):
            return "handle_registration"
        else:
            return "generate_response"
    
    def _handle_registration(self, state: RegistrationState) -> RegistrationState:
        """Fourth node (conditional): Handle the actual registration"""
        # Register the user
        user_data = {**state["user_profile"], "password": state["password"]}
        result = self.action_agent.register_user(user_data)
        
        if result["status"] == "success":
            state["status"] = RegistrationStatus.COMPLETED
            state["user_profile"]["user_id"] = result["user_id"]
            state["system_message"] = f"Registration successful! Your user ID is {result['user_id']}."
        else:
            state["status"] = RegistrationStatus.FAILED
            state["system_message"] = f"Registration failed: {result['message']}"
        
        return state
    
    def _generate_response(self, state: RegistrationState) -> RegistrationState:
        """Final node: Generate a response for the user"""
        # Only generate a response if we haven't already set one
        if "system_message" not in state or not state["system_message"]:
            response = self.action_agent.generate_response(
                state["status"].value,
                state["user_profile"],
                state["missing_fields"]
            )
            state["system_message"] = response
        
        # Save state in memory agent
        self.memory_agent.update_session(state["session_id"], {
            "user_profile": state["user_profile"],
            "status": state["status"].value,
            "missing_fields": state["missing_fields"],
            "system_message": state["system_message"]
        })
        
        return state
    
    def create_session(self) -> str:
        """Create a new session"""
        # Use memory agent to create session
        session_id = self.memory_agent.create_session()
        
        # Initialize state
        self.sessions[session_id] = {
            "session_id": session_id,
            "user_profile": {},
            "status": RegistrationStatus.INITIALIZED,
            "missing_fields": [],
            "password": "",
            "current_message": "",
            "system_message": "Hello! I'm here to help you with your registration. What would you like to do today?"
        }
        
        return session_id
    
    def process_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """Process a user message"""
        # Check if session exists
        if session_id not in self.sessions:
            session_id = self.create_session()
        
        # Get current state
        state = self.sessions[session_id].copy()  # Make a copy to avoid reference issues
        
        # Update current message
        state["current_message"] = message
        
        try:
            # Execute the graph
            result = self.graph.invoke(state)
            
            # Update session state with result
            self.sessions[session_id] = result
            
            # Prepare response
            response = {
                "session_id": session_id,
                "message": result["system_message"],
                "status": result["status"].value
            }
            
            if result["status"] == RegistrationStatus.COMPLETED and "user_id" in result["user_profile"]:
                response["user_id"] = result["user_profile"]["user_id"]
            
            if result["missing_fields"]:
                response["missing_fields"] = result["missing_fields"]
            
            return response
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "session_id": session_id,
                "message": f"I'm having trouble processing your request. Please try again.",
                "status": "error"
            }