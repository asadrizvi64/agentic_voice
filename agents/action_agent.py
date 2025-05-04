#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Action Agent
----------
Responsible for performing actions like user registration, profile updates, etc.
"""

from typing import Dict, Any, List
import traceback

class ActionAgent:
    """Agent responsible for performing actions."""
    
    def __init__(self, memory_agent):
        """
        Initialize the action agent.
        
        Args:
            memory_agent: Memory agent instance
        """
        self.memory = memory_agent
    
    def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new user.
        
        Args:
            user_data: User profile data
            
        Returns:
            Result of the registration
        """
        try:
            # Validate required fields
            required_fields = ["name", "email", "phone", "address"]
            missing_fields = [field for field in required_fields 
                            if field not in user_data or not user_data[field]]
            
            if missing_fields:
                return {
                    "status": "error",
                    "message": f"Missing required fields: {', '.join(missing_fields)}"
                }
            
            # Create user in database
            result = self.memory.store_user(user_data)
            return result
        except Exception as e:
            print(f"Error in register_user: {e}")
            traceback.print_exc()
            return {
                "status": "error",
                "message": f"Registration failed: {str(e)}"
            }
    
    def verify_profile_completeness(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify that a user profile has all required fields.
        
        Args:
            user_profile: User profile data
            
        Returns:
            Validation result
        """
        try:
            required_fields = ["name", "email", "phone", "address"]
            missing_fields = [field for field in required_fields 
                            if field not in user_profile or not user_profile[field]]
            
            if missing_fields:
                return {
                    "status": "incomplete",
                    "missing_fields": missing_fields,
                    "message": f"Missing fields: {', '.join(missing_fields)}"
                }
            
            return {
                "status": "complete",
                "message": "All required fields are present"
            }
        except Exception as e:
            print(f"Error in verify_profile_completeness: {e}")
            traceback.print_exc()
            return {
                "status": "error",
                "missing_fields": ["name", "email", "phone", "address"],
                "message": f"Error verifying profile: {str(e)}"
            }
    
    def generate_response(self, status: str, user_profile: Dict[str, Any], 
                          missing_fields: List[str] = None) -> str:
        """
        Generate a natural language response based on the current status.
        
        Args:
            status: Current status
            user_profile: User profile data
            missing_fields: Missing fields (if any)
            
        Returns:
            Natural language response
        """
        try:
            missing_fields = missing_fields or []
            
            if status == "gathering_info":
                if missing_fields:
                    missing = ", ".join(missing_fields)
                    return f"I still need your {missing} to complete your registration. Could you please provide this information?"
                return "Thank you for the information. Is there anything else you'd like to add before we complete your registration?"
            
            elif status == "password_needed":
                return "Please provide a password for your account to complete the registration."
            
            elif status == "confirming":
                profile_str = "\n".join([f"{k}: {v}" for k, v in user_profile.items() if k != "password"])
                return f"Here's the information you've provided:\n{profile_str}\n\nIs this correct? Say yes to complete your registration."
            
            elif status == "completed":
                user_id = user_profile.get("user_id", "")
                return f"Great! Your registration has been successfully completed. Your user ID is {user_id}."
            
            elif status == "error":
                return "I'm sorry, but there was a problem with your registration. Please try again."
            
            return "How can I help you with your registration today?"
        except Exception as e:
            print(f"Error in generate_response: {e}")
            traceback.print_exc()
            return "I'm here to help you with registration. Could you provide your information?"