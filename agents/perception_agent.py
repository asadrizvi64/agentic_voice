#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Perception Agent
--------------
Responsible for understanding user input, detecting intents, and extracting entities.
"""

import re
from typing import Dict, Any, Tuple, Optional, List
import traceback

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
        self.context_aware = True
    
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
        try:
            # Detect intent
            intent, confidence = self.detect_intent(text)
            
            # Extract entities
            entities = self.extract_entities(text)
            
            # Use LLM to try to extract additional entities if available
            if self.llm and not entities:
                llm_entities = self.extract_entities_with_llm(text)
                entities.update(llm_entities)
            
            print(f"Processed input: '{text}' -> intent: {intent}, confidence: {confidence}, entities: {entities}")
            
            return {
                "raw_input": text,
                "intent": intent,
                "confidence": confidence,
                "entities": entities
            }
        except Exception as e:
            print(f"Error in process_input: {e}")
            traceback.print_exc()
            return {
                "raw_input": text,
                "intent": "unknown",
                "confidence": 0.0,
                "entities": {}
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
            # Explicit name patterns
            r"(?i)name\s+(?:is\s+)?([A-Za-z\s\-'\.]+)(?:,|\.|$|\s+and)",
            r"(?i)(?:i am|i'm|this is)\s+([A-Za-z\s\-'\.]{2,})(?:,|\.|$|\s+and)",
            # Registration with name patterns
            r"(?i)register\s+(?:for|a)?\s*([A-Za-z\s\-'\.]{2,})(?:,|\.|$|\s+and|\s+with)",
            r"(?i)register\s+([A-Za-z\s\-'\.]{2,})(?:,|\.|$|\s+and|\s+with)",
            # Call me patterns
            r"(?i)call\s+me\s+([A-Za-z\s\-'\.]{2,})(?:,|\.|$|\s+and)",
            # I'm pattern
            r"(?i)I(?:'m| am)?\s+([A-Za-z\s\-'\.]{2,})(?:,|\.|$|\s+and)",
            # Just a name-like pattern at the start of the message
            r"^([A-Za-z\s\-'\.]{2,})(?:,|\.|$|\s+and)"
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, text)
            if name_match:
                name = name_match.group(1).strip()
                # Avoid capturing obvious non-names
                non_name_words = ["user", "account", "profile", "please", "would", "could", "want", "like", "hoping", 
                                "trying", "looking", "ready", "here", "interested", "need", "should"]
                if not any(word == name.lower() or word in name.lower().split() for word in non_name_words):
                    entities["name"] = name
                    break
        
        # Try to find a name if we have a multi-part string without labels
        if "name" not in entities and "," in text and len(text.split(",")) >= 2:
            parts = [p.strip() for p in text.split(",")]
            # First part might be a name if it's 1-3 words and contains only letters
            first_part = parts[0]
            if len(first_part.split()) <= 3 and re.match(r'^[A-Za-z\s\-\'\.]+$', first_part):
                non_name_words = ["user", "account", "profile", "please", "would", "could", "want", "like", "hoping", 
                               "trying", "looking", "ready", "here", "interested", "need", "should"]
                if not any(word == first_part.lower() or word in first_part.lower().split() for word in non_name_words):
                    entities["name"] = first_part
        
        # Extract email
        email_patterns = [
            r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",  # Standard email pattern
            r"(?i)email\s+(?:is|:)?\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",  # Email with label
            r"(?i)(?:contact|reach|mail)\s+(?:me|at)\s+(?:at|via)?\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)"  # Contact me at patterns
        ]
        
        for pattern in email_patterns:
            email_match = re.search(pattern, text)
            if email_match:
                entities["email"] = email_match.group(1)
                break
        
        # Extract phone - improved pattern
        phone_patterns = [
            r"(?i)phone\s+(?:number|#)?\s*(?:is|:)?\s*([0-9\s\-\+\(\)]{7,})",  # Phone with label
            r"(?<!\w)(\+?[0-9][\s\-\(\)0-9]{6,})(?!\w)",  # Standalone phone number
            r"(?i)(?:call|text|reach|contact)\s+(?:me|at)\s+(?:at|on)?\s*(\+?[0-9][\s\-\(\)0-9]{6,})",  # Contact me patterns
            r"(?i)(?:my|the)\s+number\s+(?:is|:)?\s*([0-9\s\-\+\(\)]{7,})"  # My number patterns
        ]
        
        for pattern in phone_patterns:
            phone_match = re.search(pattern, text)
            if phone_match:
                phone = phone_match.group(1).strip()
                # Clean up the phone number
                phone = re.sub(r'[^\d\+\-\(\)]', '', phone)
                if len(re.sub(r'[^\d]', '', phone)) >= 7:  # Ensure at least 7 digits
                    entities["phone"] = phone
                    break
        
        # Extract address - improved pattern
        address_patterns = [
            r"(?i)address\s+(?:is|:)?\s*(.+?)(?:\.|$|,\s*(?:phone|email|password|my))",  # Address with label
            r"(?i)(?:live|stay|reside)\s+(?:at|in|on)\s+(.+?)(?:\.|$|,\s*(?:phone|email|password|my))",  # Live at patterns
            r"(?i)(?:located|based)\s+(?:at|in|on)\s+(.+?)(?:\.|$|,\s*(?:phone|email|password|my))",  # Located at patterns
            r"(?i)(?:home|location)\s+(?:is|at|in|:)?\s*(.+?)(?:\.|$|,\s*(?:phone|email|password|my))",  # Home location patterns
            r"(?i)(?:from)\s+(.+?)(?:\.|$|,\s*(?:phone|email|password|my))"  # From patterns
        ]
        
        for pattern in address_patterns:
            address_match = re.search(pattern, text)
            if address_match:
                address = address_match.group(1).strip()
                # Check if the address has some minimum criteria
                if len(address) > 5 and any(char.isdigit() for char in address):
                    entities["address"] = address
                    break
        
        # If we don't have an address yet, look for the word "street", "road", "avenue", etc.
        if "address" not in entities:
            address_keywords = ["street", "avenue", "road", "lane", "drive", "boulevard", "court", "plaza", 
                              "parkway", "place", "way", "circle", "highway", "route", "building", "apartment"]
            for keyword in address_keywords:
                address_match = re.search(rf"(?i)(?:[\w\s]+\s+{keyword}.+?)(?:\.|$|,\s*(?:phone|email|password|my))", text)
                if address_match:
                    address = address_match.group(0).strip()
                    if len(address) > 5:
                        entities["address"] = address
                        break
        
        # If we still don't have an address, try to find a sequence with numbers and letters that might be an address
        if "address" not in entities:
            # Look for patterns like "123 Main St" or variants
            address_match = re.search(r"\b\d+\s+[\w\s\.,]+(?:street|st|avenue|ave|road|rd|lane|ln|drive|dr|boulevard|blvd|court|ct|circle|cir|plaza|plz|parkway|pkwy|highway|hwy|place|pl|way)\b", text, re.IGNORECASE)
            if address_match:
                entities["address"] = address_match.group(0).strip()
        
        # Extract password - improved patterns
        password_patterns = [
            r"(?i)password\s+(?:is|:)?\s*([A-Za-z0-9\s\-'\.\!\@\#\$\%\^\&\*\(\)]{6,})(?:,|\.|$)",  # Password with label
            r"(?i)(?:use|set|my)\s+password\s+(?:as|to|:)?\s*([A-Za-z0-9\s\-'\.\!\@\#\$\%\^\&\*\(\)]{6,})(?:,|\.|$)",  # Use password as patterns
            r"(?i)(?:login|signin|sign in)\s+(?:with|using)\s+(?:password|pwd)?\s*([A-Za-z0-9\s\-'\.\!\@\#\$\%\^\&\*\(\)]{6,})(?:,|\.|$)"  # Login with patterns
        ]
        
        for pattern in password_patterns:
            password_match = re.search(pattern, text)
            if password_match:
                entities["password"] = password_match.group(1).strip()
                break
        
        # Check for standalone password (if it's a single "word" and no other entities extracted)
        if "password" not in entities and not any(k in entities for k in ["name", "email", "phone", "address"]):
            potential_password = text.strip()
            if re.match(r'^[A-Za-z0-9\!\@\#\$\%\^\&\*\(\)]{6,20}$', potential_password):
                entities["password"] = potential_password
        
        return entities
    
    def extract_entities_with_llm(self, text: str) -> Dict[str, Any]:
        """
        Use the LLM to extract entities from text.
        
        Args:
            text: User message
            
        Returns:
            Dictionary of extracted entities
        """
        if self.llm is None:
            return {}
        
        try:
            prompt = f"""
            Extract user registration information from the following text.
            Text: "{text}"

            Consider context and look for information that could be:
            - Name (a person's name)
            - Email (must be in valid email format)
            - Phone number (digits, can have formatting like parentheses, dashes)
            - Address (any location information)
            - Password (if explicitly mentioned)

            Return ONLY the extracted information in this exact JSON format:
            {{
              "name": "extracted name or null",
              "email": "extracted email or null",
              "phone": "extracted phone or null",
              "address": "extracted address or null",
              "password": "extracted password or null"
            }}
            
            DO NOT include any other text in your response.
            """
            
            response = self.llm.invoke(prompt)
            
            # Try to extract JSON from the response
            import json
            import re
            
            # Look for JSON in the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group(0)
                    extracted = json.loads(json_str)
                    
                    # Filter out null/None values
                    entities = {}
                    for key, value in extracted.items():
                        if value and value.lower() not in ["null", "none", "n/a", ""]:
                            entities[key] = value
                    
                    return entities
                except json.JSONDecodeError:
                    print("Failed to parse JSON from LLM response")
            
            return {}
        except Exception as e:
            print(f"Error in extract_entities_with_llm: {e}")
            traceback.print_exc()
            return {}