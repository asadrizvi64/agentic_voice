#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Perception Agent
--------------
Responsible for understanding user input, detecting intents, and extracting entities.
"""

import re
from typing import Dict, Any, Tuple, Optional
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

class PerceptionAgent:
    """Agent responsible for understanding user input."""
    
    def __init__(self, llm=None):
        """
        Initialize the perception agent
        
        Args:
            llm: LLM instance (Ollama or any other LangChain compatible LLM)
        """
        self.intent_patterns = self._initialize_intent_patterns()
        self.llm = llm
    
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
        
        print(f"Processed input: '{text}' -> intent: {intent}, confidence: {confidence}, entities: {entities}")
        
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
        
        # Extract name - improved pattern to handle more formats
        name_patterns = [
            r"(?i)name\s+(?:is\s+)?([A-Za-z\s\-'\.]+)(?:,|\.|$|\s+and)",
            r"(?i)(?:i am|i'm|this is)\s+([A-Za-z\s\-'\.]{2,})(?:,|\.|$|\s+and)",
            r"(?i)register\s+(?:for|a)?\s*([A-Za-z\s\-'\.]{2,})(?:,|\.|$|\s+and|\s+with)",
            r"(?i)register\s+([A-Za-z\s\-'\.]{2,})(?:,|\.|$|\s+and|\s+with)"
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, text)
            if name_match:
                name = name_match.group(1).strip()
                # Avoid capturing obvious non-names
                if not any(word in name.lower() for word in ["user", "account", "profile", "please", "would", "could", "want", "like"]):
                    entities["name"] = name
                    break
        
        # Extract email
        email_match = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", text)
        if email_match:
            entities["email"] = email_match.group(1)
        
        # Extract phone - improved pattern
        phone_patterns = [
            r"(?i)phone\s+(?:number\s+)?(?:is\s+)?([0-9\s\-\+\(\)]{7,})",
            r"(?<!\w)(\+?[0-9][\s\-\(\)0-9]{6,})(?!\w)",
            r"(?i)at\s+(\+?[0-9][\s\-\(\)0-9]{6,})"
        ]
        
        for pattern in phone_patterns:
            phone_match = re.search(pattern, text)
            if phone_match:
                entities["phone"] = phone_match.group(1).strip()
                break
        
        # Extract address - improved pattern
        address_patterns = [
            r"(?i)address\s+(?:is\s+)?(.+?)(?:\.|$)",
            r"(?i)(?:at|on|live\s+at)\s+(\d+\s+[A-Za-z\s\.\,]+)",
            r"(?i)staying\s+(?:at|in)\s+(.+?)(?:\.|$)",
            r"(?i)located\s+(?:at|in)\s+(.+?)(?:\.|$)"
        ]
        
        for pattern in address_patterns:
            address_match = re.search(pattern, text)
            if address_match:
                entities["address"] = address_match.group(1).strip()
                break
        
        # Extract password
        password_match = re.search(r"(?i)password\s+(?:is\s+)?([A-Za-z0-9\s\-'\.\!\@\#\$\%\^\&\*\(\)]{6,})(?:,|\.|$)", text)
        if password_match:
            entities["password"] = password_match.group(1).strip()
        
        # Special case for registration with name in a simple format
        if "register" in text.lower() and "name" not in entities:
            # Try to find a name after "register"
            register_name_match = re.search(r"(?i)register\s+(?:a\s+)?(?:user\s+)?(?:for\s+)?([A-Za-z\s\-'\.]{2,})(?:,|\.|$|\s+and)", text)
            if register_name_match:
                name = register_name_match.group(1).strip()
                # Avoid capturing obvious non-names
                if len(name.split()) <= 3 and not any(word in name.lower() for word in ["user", "account", "profile", "please", "would", "could", "want", "like", "this", "then"]):
                    entities["name"] = name
        
        return entities