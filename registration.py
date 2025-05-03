#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Registration workflow using LangGraph
"""

import re
import uuid
from typing import Dict, List, Any, TypedDict, Literal
from enum import Enum

import langgraph.graph as lg
from langgraph.graph import END, StateGraph
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from db import SimpleDB

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

class RegistrationSystem:
    """Registration system using LangGraph workflow"""
    
    def __init__(self, api_key=None, model="gpt-3.5-turbo"):
        """Initialize the registration system"""
        self.db = SimpleDB()
        self.sessions = {}
        
        # Setup LLM
        if api_key:
            self.llm = ChatOpenAI(api_key=api_key, temperature=0, model=model)
        else:
            # Use mock LLM for demo
            self.llm = self._create_mock_llm()
        
        # Build the graph
        self.graph = self._build_registration_graph()
    
    def _create_mock_llm(self):
        """Create a mock LLM for demo purposes"""
        class MockLLM:
            def invoke(self, messages):
                """Mock LLM invocation"""
                user_message = ""
                for message in messages:
                    if isinstance(message, HumanMessage):
                        user_message = message.content
                        break
                
                if "register" in user_message.lower():
                    return HumanMessage(content="I'll help you register. Please provide your name, email, phone, and address.")
                elif any(field in user_message.lower() for field in ["name", "email", "phone", "address"]):
                    return HumanMessage(content="Thanks for providing that information. I've recorded it.")
                elif "password" in user_message.lower():
                    return HumanMessage(content="Thank you for providing a password. Let me confirm the information you've provided.")
                elif any(word in user_message.lower() for word in ["yes", "correct", "confirm"]):
                    return HumanMessage(content="Great! Your registration is now complete.")
                else:
                    return HumanMessage(content="I'm not sure what you mean. Can you provide more information?")
        
        return MockLLM()
    
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
        # Extract entities from the initial message
        entities = self._extract_user_information(state["current_message"])
        
        # Update user profile
        for key, value in entities.items():
            if key == "password":
                state["password"] = value
            else:
                state["user_profile"][key] = value
        
        # Update status based on extracted information
        state["status"] = RegistrationStatus.GATHERING_INFO
        
        # Add system message
        state["system_message"] = "Registration process initialized. Collecting user information."
        
        return state
    
    def _identify_missing_info(self, state: RegistrationState) -> RegistrationState:
        """Identify missing information in the user profile"""
        # Check required fields
        required_fields = ["name", "email", "phone", "address"]
        missing_fields = [field for field in required_fields 
                         if field not in state["user_profile"] or not state["user_profile"][field]]
        
        state["missing_fields"] = missing_fields
        
        if not missing_fields:
            # All required fields are present
            if state["password"]:
                state["status"] = RegistrationStatus.CONFIRMING
                state["system_message"] = "All information provided. Ready to complete registration."
            else:
                state["status"] = RegistrationStatus.PASSWORD_NEEDED
                state["system_message"] = "Please provide a password to complete your registration."
        else:
            # Missing fields
            missing = ", ".join(missing_fields)
            state["system_message"] = f"Missing information: {missing}. Please provide this information."
        
        return state
    
    def _process_user_input(self, state: RegistrationState) -> RegistrationState:
        """Process user input and update the state"""
        # Extract information from the user message
        entities = self._extract_user_information(state["current_message"])
        
        # Update user profile
        for key, value in entities.items():
            if key == "password":
                state["password"] = value
            else:
                state["user_profile"][key] = value
        
        return state
    
    def _register_user(self, state: RegistrationState) -> RegistrationState:
        """Register the user with the provided information"""
        # Create the user in the database
        result = self.db.create_user({
            **state["user_profile"],
            "password": state["password"]
        })
        
        if result["status"] == "success":
            state["status"] = RegistrationStatus.COMPLETED
            state["user_profile"]["user_id"] = result["user_id"]
            state["system_message"] = f"Registration completed successfully! Your user ID is {result['user_id']}."
        else:
            state["status"] = RegistrationStatus.FAILED
            state["system_message"] = f"Registration failed: {result['message']}"
        
        return state
    
    def _generate_response(self, state: RegistrationState) -> RegistrationState:
        """Generate a response based on the current state"""
        # Save current state to database
        self.db.update_session(state["session_id"], {
            "user_profile": state["user_profile"],
            "status": state["status"],
            "missing_fields": state["missing_fields"],
            "system_message": state["system_message"]
        })
        
        return state
    
    def _should_collect_info(self, state: RegistrationState) -> bool:
        """Check if we need to collect more information"""
        return len(state["missing_fields"]) > 0
    
    def _should_register(self, state: RegistrationState) -> bool:
        """Check if we're ready to register the user"""
        has_required_fields = all(field in state["user_profile"] and state["user_profile"][field] 
                                for field in ["name", "email", "phone", "address"])
        has_password = state["password"] is not None and len(state["password"]) > 0
        user_confirmed = "yes" in state["current_message"].lower() or "correct" in state["current_message"].lower()
        
        return (has_required_fields and has_password and 
                state["status"] == RegistrationStatus.CONFIRMING and user_confirmed)
    
    def _extract_user_information(self, message: str) -> Dict[str, Any]:
        """Extract user information from a message"""
        entities = {}
        
        # Extract name
        name_match = re.search(r"(?i)name\s+(?:is\s+)?([A-Za-z\s\-'\.]+)(?:,|\.|$|\s+and)", message)
        if name_match:
            entities["name"] = name_match.group(1).strip()
        
        # Extract email
        email_match = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", message)
        if email_match:
            entities["email"] = email_match.group(1)
        
        # Extract phone
        phone_match = re.search(r"(?i)phone\s+(?:number\s+)?(?:is\s+)?([0-9\s\-\+\(\)]{7,})", message)
        if phone_match:
            entities["phone"] = phone_match.group(1).strip()
        
        # Extract address
        address_match = re.search(r"(?i)address\s+(?:is\s+)?(.+?)(?:\.|$)", message)
        if address_match:
            entities["address"] = address_match.group(1).strip()
        
        # Extract password
        password_match = re.search(r"(?i)password\s+(?:is\s+)?([A-Za-z0-9\s\-'\.\!\@\#\$\%\^\&\*\(\)]{6,})(?:,|\.|$)", message)
        if password_match:
            entities["password"] = password_match.group(1).strip()
        
        return entities
    
    def create_session(self) -> str:
        """Create a new session"""
        session_id = self.db.create_session()
        
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
        state = self.sessions[session_id]
        
        # Update current message
        state["current_message"] = message
        
        # Run the graph
        for event in self.graph.stream(state):
            state = event.state
        
        # Update session state
        self.sessions[session_id] = state
        
        # Prepare response
        response = {
            "session_id": session_id,
            "message": state["system_message"],
            "status": state["status"]
        }
        
        if state["status"] == RegistrationStatus.COMPLETED and "user_id" in state["user_profile"]:
            response["user_id"] = state["user_profile"]["user_id"]
        
        if state["missing_fields"]:
            response["missing_fields"] = state["missing_fields"]
        
        return response