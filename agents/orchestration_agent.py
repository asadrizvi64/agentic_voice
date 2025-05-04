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
import traceback
import json
import sys
import os

# Import Ollama instead of ChatOpenAI
from langchain_community.llms import Ollama

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
        print(f"Initializing OrchestrationAgent with Ollama: base_url={base_url}, model={model}")
        
        # Initialize Ollama
        try:
            ollama_llm = Ollama(
                model=model,
                base_url=base_url
            )
            print("Ollama initialized successfully")
        except Exception as e:
            print(f"Error initializing Ollama: {e}")
            traceback.print_exc()
            ollama_llm = None
        
        # Initialize agents
        self.memory_agent = MemoryAgent()
        self.perception_agent = PerceptionAgent(llm=ollama_llm)
        self.action_agent = ActionAgent(self.memory_agent)
        
        # Session storage
        self.sessions = {}
        
        # Build the workflow graph
        try:
            self.graph = self._build_registration_graph()
            print("Registration graph built successfully")
        except Exception as e:
            print(f"Error building registration graph: {e}")
            traceback.print_exc()
            self.graph = None
    
    def _build_registration_graph(self):
        """Build the graph for the registration workflow"""
        # Create the graph
        builder = StateGraph(RegistrationState)
        
        # Add nodes
        builder.add_node("initialize", self._initialize_state)
        builder.add_node("identify_missing_info", self._identify_missing_info)
        builder.add_node("process_input", self._process_user_input)
        builder.add_node("register_user", self._register_user)
        builder.add_node("generate_response", self._generate_response)
        
        # Add edges
        builder.add_edge("initialize", "identify_missing_info")
        builder.add_edge("identify_missing_info", "process_input")
        
        # Add conditional edges
        builder.add_conditional_edges(
            "process_input",
            # Decision function to determine next node
            lambda state: (
                "register_user" if self._should_register(state) else
                "identify_missing_info" if self._should_collect_info(state) else
                "generate_response"
            ),
            {
                "register_user": "register_user",
                "identify_missing_info": "identify_missing_info",
                "generate_response": "generate_response"
            }
        )
        
        builder.add_edge("register_user", "generate_response")
        
        # Add conditional edge from generate_response to either END or process_input
        builder.add_conditional_edges(
            "generate_response",
            lambda state: END if state["status"] in [RegistrationStatus.COMPLETED, RegistrationStatus.FAILED] else "process_input",
            {
                END: END,
                "process_input": "process_input"
            }
        )
        
        # Set entry point
        builder.set_entry_point("initialize")
        
        # Compile the graph
        return builder.compile()
    
    def _initialize_state(self, state: RegistrationState) -> RegistrationState:
        """Initialize the registration process state"""
        print(f"Initializing state with message: {state['current_message']}")
        try:
            # Use perception agent to extract entities
            perception_result = self.perception_agent.process_input(state["current_message"])
            print(f"Perception result: {perception_result}")
            entities = perception_result["entities"]
            
            # Update user profile
            for key, value in entities.items():
                if key == "password":
                    state["password"] = value
                else:
                    state["user_profile"][key] = value
            
            # Update status based on extracted information
            state["status"] = RegistrationStatus.GATHERING_INFO
            
            # Add system message
            state["system_message"] = "I'll help you register. "
            
            if "name" in entities:
                state["system_message"] += f"I've recorded your name as {entities['name']}. "
            
            if len(entities) > 0:
                state["system_message"] += "What else would you like to provide? We need your name, email, phone, and address to complete registration."
            else:
                state["system_message"] += "Please provide your name, email, phone, and address to complete registration."
            
            print(f"Updated state: {state}")
        except Exception as e:
            print(f"Error in initialize_state: {e}")
            traceback.print_exc()
            state["system_message"] = "I'll help you register. Please provide your name, email, phone, and address."
        
        return state
    
    def _identify_missing_info(self, state: RegistrationState) -> RegistrationState:
        """Identify missing information in the user profile"""
        print(f"Identifying missing info for profile: {state['user_profile']}")
        try:
            # Use action agent to verify profile completeness
            result = self.action_agent.verify_profile_completeness(state["user_profile"])
            print(f"Profile completeness result: {result}")
            
            state["missing_fields"] = result.get("missing_fields", [])
            
            if result["status"] == "complete":
                # All required fields are present
                if state["password"]:
                    state["status"] = RegistrationStatus.CONFIRMING
                    state["system_message"] = "All information provided. Ready to complete registration."
                else:
                    state["status"] = RegistrationStatus.PASSWORD_NEEDED
                    state["system_message"] = "Please provide a password to complete your registration."
            else:
                # Missing fields
                state["system_message"] = result["message"]
            
            print(f"Updated state after missing info check: {state}")
        except Exception as e:
            print(f"Error in identify_missing_info: {e}")
            traceback.print_exc()
            state["missing_fields"] = ["name", "email", "phone", "address"]
            state["system_message"] = "I need your complete information to process the registration."
        
        return state
    
    def _process_user_input(self, state: RegistrationState) -> RegistrationState:
        """Process user input and update the state"""
        print(f"Processing user input: {state['current_message']}")
        try:
            # Use perception agent to extract entities
            perception_result = self.perception_agent.process_input(state["current_message"])
            print(f"Perception result: {perception_result}")
            entities = perception_result["entities"]
            
            # Update user profile
            for key, value in entities.items():
                if key == "password":
                    state["password"] = value
                else:
                    state["user_profile"][key] = value
            
            print(f"Updated state after processing input: {state}")
        except Exception as e:
            print(f"Error in process_user_input: {e}")
            traceback.print_exc()
            # Don't update state if there's an error
        
        return state
    
    def _register_user(self, state: RegistrationState) -> RegistrationState:
        """Register the user with the provided information"""
        print(f"Registering user with profile: {state['user_profile']}")
        try:
            # Use action agent to register the user
            user_data = {**state["user_profile"], "password": state["password"]}
            result = self.action_agent.register_user(user_data)
            print(f"Registration result: {result}")
            
            if result["status"] == "success":
                state["status"] = RegistrationStatus.COMPLETED
                state["user_profile"]["user_id"] = result["user_id"]
                state["system_message"] = result["message"]
            else:
                state["status"] = RegistrationStatus.FAILED
                state["system_message"] = result["message"]
            
            print(f"Updated state after registration: {state}")
        except Exception as e:
            print(f"Error in register_user: {e}")
            traceback.print_exc()
            state["status"] = RegistrationStatus.FAILED
            state["system_message"] = f"Registration failed due to a system error: {str(e)}"
        
        return state
    
    def _generate_response(self, state: RegistrationState) -> RegistrationState:
        """Generate a response based on the current state"""
        print(f"Generating response for state: {state}")
        try:
            # Use action agent to generate response
            response = self.action_agent.generate_response(
                state["status"].value,
                state["user_profile"],
                state["missing_fields"]
            )
            
            state["system_message"] = response
            print(f"Generated response: {response}")
            
            # Save state in memory agent
            self.memory_agent.update_session(state["session_id"], {
                "user_profile": state["user_profile"],
                "status": state["status"].value,
                "missing_fields": state["missing_fields"],
                "system_message": state["system_message"]
            })
        except Exception as e:
            print(f"Error in generate_response: {e}")
            traceback.print_exc()
            # Keep existing system message if there's an error
        
        return state
    
    def _should_collect_info(self, state: RegistrationState) -> bool:
        """Check if we need to collect more information"""
        return len(state["missing_fields"]) > 0
    
    def _should_register(self, state: RegistrationState) -> bool:
        """Check if we're ready to register the user"""
        has_required_fields = len(state["missing_fields"]) == 0
        has_password = state["password"] is not None and len(state["password"]) > 0
        user_confirmed = "yes" in state["current_message"].lower() or "correct" in state["current_message"].lower()
        
        return (has_required_fields and has_password and 
                state["status"] == RegistrationStatus.CONFIRMING and user_confirmed)
    
    def create_session(self) -> str:
        """Create a new session"""
        print("Creating new session")
        try:
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
            
            print(f"Session created: {session_id}")
            return session_id
        except Exception as e:
            print(f"Error creating session: {e}")
            traceback.print_exc()
            # Generate a simple session ID if the memory agent fails
            import uuid
            session_id = f"fallback_session_{uuid.uuid4().hex[:8]}"
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
        print(f"Processing message: '{message}' for session: {session_id}")
        
        # Check if session exists
        if session_id not in self.sessions:
            print(f"Session {session_id} not found, creating new session")
            session_id = self.create_session()
        
        # Get current state
        state = self.sessions[session_id]
        
        # Update current message
        state["current_message"] = message
        
        # Run the graph
        try:
            print("Running state graph...")
            # Deep copy state for debug purposes
            initial_state = json.dumps(state)
            
            events = list(self.graph.stream(state))
            print(f"Graph stream completed with {len(events)} events")
            
            # Process events and update state
            for i, event in enumerate(events):
                print(f"Processing event {i+1}/{len(events)}: {type(event)}")
                
                if hasattr(event, 'state'):
                    state = event.state
                    print(f"State updated from event.state")
                elif hasattr(event, 'updates') and event.updates:
                    print(f"Event has updates: {event.updates}")
                    # This is likely an AddableUpdatesDict
                    # We can try to apply updates manually
                    try:
                        for key, value in event.updates.items():
                            if key in state:
                                state[key] = value
                                print(f"Updated state[{key}] manually")
                    except Exception as update_err:
                        print(f"Error applying updates: {update_err}")
                else:
                    print(f"Unknown event type or structure: {event}")
                    
            # Check if state was actually updated
            if initial_state == json.dumps(state):
                print("WARNING: State did not change after graph execution!")
                # Add a fallback response
                state["system_message"] = f"I've received your message: '{message}'. Please provide your registration information (name, email, phone, address)."
                
        except Exception as e:
            print(f"Error running graph: {e}")
            traceback.print_exc()
            # Set a fallback response
            state["system_message"] = f"I've received your message: '{message}'. Let me help you with your registration."
        
        # Update session state
        self.sessions[session_id] = state
        print(f"Final state: {state}")
        
        # Prepare response
        response = {
            "session_id": session_id,
            "message": state["system_message"],
            "status": state["status"].value if isinstance(state["status"], RegistrationStatus) else state["status"]
        }
        
        if state["status"] == RegistrationStatus.COMPLETED and "user_id" in state["user_profile"]:
            response["user_id"] = state["user_profile"]["user_id"]
        
        if state["missing_fields"]:
            response["missing_fields"] = state["missing_fields"]
        
        print(f"Returning response: {response}")
        return response