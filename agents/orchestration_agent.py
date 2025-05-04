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
import re

# Import Ollama
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate

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
    conversation_history: List[Dict[str, str]]

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
            self.llm = Ollama(
                model=model,
                base_url=base_url
            )
            print("Ollama initialized successfully")
        except Exception as e:
            print(f"Error initializing Ollama: {e}")
            traceback.print_exc()
            self.llm = None
        
        # Initialize agents
        self.memory_agent = MemoryAgent()
        self.perception_agent = PerceptionAgent(llm=self.llm)
        self.action_agent = ActionAgent(self.memory_agent)
        
        # Session storage
        self.sessions = {}
        
        # Response templates
        self.response_templates = self._initialize_response_templates()
    
    def _initialize_response_templates(self):
        """Initialize templates for dynamic responses"""
        return {
            "welcome": PromptTemplate(
                input_variables=["user_name"],
                template="Hello{user_name}! I'm here to help you with your registration. What would you like to do today?"
            ),
            "gathering_info": PromptTemplate(
                input_variables=["profile", "missing_fields"],
                template="""Given the following user profile information:
    Profile: {profile}
    Missing Fields: {missing_fields}

    Generate a friendly, conversational response that:
    1. Acknowledges any information that was provided
    2. Naturally asks for the missing information without using labels like "name:", "email:", etc.
    3. Maintains a warm, helpful tone

    Response:"""
            ),
            "password_needed": PromptTemplate(
                input_variables=["profile"],
                template="""Given the following user profile information:
    Profile: {profile}

    Generate a friendly response that:
    1. Thanks the user for providing their information
    2. Naturally asks for a password to complete registration
    3. Maintains a warm, helpful tone

    Response:"""
            ),
            "confirming": PromptTemplate(
                input_variables=["profile"],
                template="""Given the following user profile information:
    Profile: {profile}

    Generate a confirmation message that:
    1. Displays the collected information in a clear format
    2. Asks the user to confirm if the information is correct to complete registration
    3. Maintains a warm, helpful tone

    Response:"""
            ),
            "completed": PromptTemplate(
                input_variables=["user_id", "profile"],
                template="""Given the following user registration result:
    User ID: {user_id}
    Profile: {profile}

    Generate a friendly completion message that:
    1. Congratulates the user on successful registration
    2. Mentions their user ID
    3. Briefly explains what they can do next
    4. Maintains a warm, helpful tone

    Response:"""
            ),
            "failed": PromptTemplate(
                input_variables=["error"],
                template="""Given the following registration error:
    Error: {error}

    Generate a sympathetic response that:
    1. Apologizes for the issue
    2. Explains what went wrong in simple terms
    3. Suggests what they might try next
    4. Maintains a warm, helpful tone

    Response:"""
            )
        }

    def _generate_llm_response(self, template_key, **kwargs):
        """Generate a dynamic response using the LLM"""
        if self.llm is None:
            # Fallback responses if LLM is not available
            if template_key == "welcome":
                return f"Hello! I'm here to help you with your registration. What would you like to do today?"
            elif template_key == "gathering_info":
                missing = kwargs.get("missing_fields", [])
                missing_str = ", ".join(missing) if missing else "information"
                return f"I need your {missing_str} to complete registration. Could you please provide this?"
            elif template_key == "password_needed":
                return "Please provide a password to complete your registration."
            elif template_key == "confirming":
                profile = kwargs.get("profile", {})
                profile_str = "\n".join([f"{k}: {v}" for k, v in profile.items() if k != "password"])
                return f"Here's the information you've provided:\n{profile_str}\n\nIs this correct? Say yes to complete your registration."
            elif template_key == "completed":
                user_id = kwargs.get("user_id", "")
                return f"Great! Your registration has been successfully completed. Your user ID is {user_id}."
            elif template_key == "failed":
                error = kwargs.get("error", "")
                return f"I'm sorry, but there was a problem with your registration: {error}. Please try again."
            else:
                return "How can I help you with your registration today?"
        
        try:
            # Get the appropriate template
            template = self.response_templates.get(template_key)
            if not template:
                print(f"Template '{template_key}' not found")
                return "How can I help you with your registration today?"
            
            # Format the prompt
            prompt = template.format(**kwargs)
            
            # Generate the response
            response = self.llm.invoke(prompt)
            
            # Clean up the response
            response = response.strip()
            
            # Add special handling for confirming template
            if template_key == "confirming" and kwargs.get("profile"):
                # Ensure the profile info is clearly visible, even if the LLM doesn't format it well
                profile = kwargs.get("profile", {})
                profile_str = "\n".join([f"{k}: {v}" for k, v in profile.items() if k != "password"])
                if not re.search(r'name:.+email:.+phone:.+address', response, re.DOTALL | re.IGNORECASE):
                    response = f"Here's the information you've provided:\n{profile_str}\n\nIs this correct? Say yes to complete your registration."
            
            return response
        except Exception as e:
            print(f"Error generating LLM response: {e}")
            traceback.print_exc()
            # Fall back to template-based response
            if template_key == "welcome":
                return f"Hello! I'm here to help you with your registration. What would you like to do today?"
            elif template_key == "gathering_info":
                missing = kwargs.get("missing_fields", [])
                missing_str = ", ".join(missing) if missing else "information"
                return f"I need your {missing_str} to complete registration. Could you please provide this?"
            elif template_key == "password_needed":
                return "Please provide a password to complete your registration."
            elif template_key == "confirming":
                profile = kwargs.get("profile", {})
                profile_str = "\n".join([f"{k}: {v}" for k, v in profile.items() if k != "password"])
                return f"Here's the information you've provided:\n{profile_str}\n\nIs this correct? Say yes to complete your registration."
            elif template_key == "completed":
                user_id = kwargs.get("user_id", "")
                return f"Great! Your registration has been successfully completed. Your user ID is {user_id}."
            elif template_key == "failed":
                error = kwargs.get("error", "")
                return f"I'm sorry, but there was a problem with your registration: {error}. Please try again."
            else:
                return "How can I help you with your registration today?"
    
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
                "system_message": self._generate_llm_response("welcome", user_name=""),
                "conversation_history": []
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
                "system_message": "Hello! I'm here to help you with your registration. What would you like to do today?",
                "conversation_history": []
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
        state = self.sessions[session_id].copy()  # Make a copy to avoid issues
        
        # Update current message
        state["current_message"] = message
        
        # Add to conversation history
        state["conversation_history"].append({"role": "user", "content": message})
        
        try:
            # Extract entities from the message
            perception_result = self.perception_agent.process_input(message)
            entities = perception_result["entities"]
            
            # Update user profile with extracted entities
            for key, value in entities.items():
                if key == "password":
                    state["password"] = value
                else:
                    state["user_profile"][key] = value
            
            print(f"Updated profile: {state['user_profile']}")
            
            # Check for missing information
            result = self.action_agent.verify_profile_completeness(state["user_profile"])
            state["missing_fields"] = result.get("missing_fields", [])
            print(f"Missing fields: {state['missing_fields']}")
            
            # Update status based on current state
            if len(state["missing_fields"]) == 0:
                if not state["password"]:
                    state["status"] = RegistrationStatus.PASSWORD_NEEDED
                    state["system_message"] = self._generate_llm_response(
                        "password_needed", 
                        profile=state["user_profile"]
                    )
                else:
                    # All info collected, move to confirmation
                    state["status"] = RegistrationStatus.CONFIRMING
                    state["system_message"] = self._generate_llm_response(
                        "confirming", 
                        profile=state["user_profile"]
                    )
            else:
                # Still missing information
                state["status"] = RegistrationStatus.GATHERING_INFO
                state["system_message"] = self._generate_llm_response(
                    "gathering_info", 
                    profile=state["user_profile"],
                    missing_fields=state["missing_fields"]
                )
            
            # Check if the user has confirmed and we should register
            if state["status"] == RegistrationStatus.CONFIRMING and \
               ("yes" in message.lower() or "correct" in message.lower()):
                # Register the user
                user_data = {**state["user_profile"], "password": state["password"]}
                result = self.action_agent.register_user(user_data)
                
                if result["status"] == "success":
                    state["status"] = RegistrationStatus.COMPLETED
                    state["user_profile"]["user_id"] = result["user_id"]
                    state["system_message"] = self._generate_llm_response(
                        "completed", 
                        user_id=result["user_id"],
                        profile=state["user_profile"]
                    )
                else:
                    state["status"] = RegistrationStatus.FAILED
                    state["system_message"] = self._generate_llm_response(
                        "failed", 
                        error=result["message"]
                    )
            
        except Exception as e:
            print(f"Error processing message: {e}")
            traceback.print_exc()
            state["system_message"] = f"I've received your message, but I'm having trouble processing it. Could you please provide your information clearly? I need your name, email, phone number, and address for registration."
        
        # Add to conversation history
        state["conversation_history"].append({"role": "assistant", "content": state["system_message"]})
        
        # Update session state
        self.sessions[session_id] = state
        
        # Save state in memory agent
        try:
            self.memory_agent.update_session(state["session_id"], {
                "user_profile": state["user_profile"],
                "status": state["status"].value,
                "missing_fields": state["missing_fields"],
                "system_message": state["system_message"],
                "conversation_history": state["conversation_history"]
            })
        except Exception as e:
            print(f"Error saving session: {e}")
            traceback.print_exc()
        
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