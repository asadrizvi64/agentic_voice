#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Perception Agent
--------------
Responsible for understanding user input, detecting intents, and extracting entities.
"""

import re
from typing import Dict, Any, Tuple
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

class PerceptionAgent:
    """Agent responsible for understanding user input."""
    
    def __init__(self, api_key=None, model="gpt-3.5-turbo"):
        """Initialize the perception agent"""
        self.intent_patterns = self._initialize_intent_patterns()
        
        # Set up LLM if API key provided
        if api_key:
            self.llm = ChatOpenAI(api_key=api_key, temperature=0, model=model)
        else:
            self.llm = None
    
    def _initialize_intent_patterns(self):
        """Initialize intent detection patterns"""
        return {
            "register": [
                r"(?i)(register|sign up|create account)",
                r"(?i)want.*to.*(register|complete profile)",
                r"(?i)complete.*(registration|profile)"
            ],
            "update_information": [
                r"(?i)(update|change|modify).*(profile|information)",
                r"(?i)edit.*profile"
            ],
            "view_profile": [
                r"(?i)(view|see|get|my).*(profile|information)",
                r"(?i)show.*profile"
            ]
        }
    
    def process_input(self, text: str) -> Dict[str, Any]:
        """
        Process user input to extract intent and entities.
        
        Args:
            text: User message
            
        Returns:
            Dictionary with intent, confidence, and entities
        """
        # Detect intent
        intent, confidence = self.detect_intent(text)
        
        # Extract entities
        entities = self.extract_entities(text)
        
        return {
            "raw_input": text,
            "intent": intent,
            "confidence": confidence,
            "entities": entities
        }
    
    def detect_intent(self, text: str) -> Tuple[str, float]:
        """
        Detect the user's intent from text.
        
        Args:
            text: User message
            
        Returns:
            Tuple of (intent, confidence)
        """
        best_intent = "unknown"
        highest_confidence = 0.0
        
        # Check each intent pattern
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    match = re.search(pattern, text)
                    match_length = match.end() - match.start()
                    confidence = min(0.5 + (match_length / len(text)) * 0.5, 0.95)
                    
                    if confidence > highest_confidence:
                        highest_confidence = confidence
                        best_intent = intent
        
        # Default to register intent if providing information
        if best_intent == "unknown" and any(item in text.lower() for item in ["name", "email", "phone", "address"]):
            best_intent = "register"
            highest_confidence = 0.7
        
        return best_intent, highest_confidence
    
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract entities from text using regex patterns.
        
        Args:
            text: User message
            
        Returns:
            Dictionary of extracted entities
        """
        entities = {}
        
        # Extract name
        name_match = re.search(r"(?i)name\s+(?:is\s+)?([A-Za-z\s\-'\.]+)(?:,|\.|$|\s+and)", text)
        if name_match:
            entities["name"] = name_match.group(1).strip()
        
        # Extract email
        email_match = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", text)
        if email_match:
            entities["email"] = email_match.group(1)
        
        # Extract phone
        phone_match = re.search(r"(?i)phone\s+(?:number\s+)?(?:is\s+)?([0-9\s\-\+\(\)]{7,})", text)
        if phone_match:
            entities["phone"] = phone_match.group(1).strip()
        else:
            # Try alternative phone pattern
            phone_match = re.search(r"(?<!\w)(\+?[0-9][\s\-\(\)0-9]{6,})(?!\w)", text)
            if phone_match:
                entities["phone"] = phone_match.group(1).strip()
        
        # Extract address
        address_match = re.search(r"(?i)address\s+(?:is\s+)?(.+?)(?:\.|$)", text)
        if address_match:
            entities["address"] = address_match.group(1).strip()
        else:
            # Try alternative address pattern
            address_match = re.search(r"(?i)(?:at|on|live\s+at)\s+(\d+\s+[A-Za-z\s\.\,]+)", text)
            if address_match:
                entities["address"] = address_match.group(1).strip()
        
        # Extract password
        password_match = re.search(r"(?i)password\s+(?:is\s+)?([A-Za-z0-9\s\-'\.\!\@\#\$\%\^\&\*\(\)]{6,})(?:,|\.|$)", text)
        if password_match:
            entities["password"] = password_match.group(1).strip()
        
        return entities