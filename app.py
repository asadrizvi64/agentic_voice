#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Multi-Agent Registration System
-----------------------------
A demonstration of multi-agent architecture for user registration.
"""

import tkinter as tk
import threading
import sys
import json
import argparse
import os

from agents.orchestration_agent import OrchestrationAgent
from chat_interface import ChatInterface

def run_chat_interface():
    """Run the chat interface with TTS/STT"""
    root = tk.Tk()
    app = ChatInterface(root)
    root.mainloop()

def run_command_line(args):
    """Run in command line mode"""
    # Initialize the orchestration agent
    orchestration_agent = OrchestrationAgent()
    
    # Create session
    session_id = orchestration_agent.create_session()
    print(f"Session created: {session_id}")
    
    # Print agent information
    print("\n=== Multi-Agent Registration System ===")
    print("Agents:")
    print("  - Perception Agent: Extracts intents and entities from user messages")
    print("  - Memory Agent: Manages persistent storage of user information")
    print("  - Action Agent: Executes registration actions and validation")
    print("  - Orchestration Agent: Coordinates workflow between agents\n")
    
    # Print welcome message
    print("System: Hello! I'm here to help you with your registration. What would you like to do today?")
    
    # Process single message if provided
    if args.message:
        print(f"\nYou: {args.message}")
        response = orchestration_agent.process_message(session_id, args.message)
        print(f"\nSystem: {response['message']}")
        print(f"Status: {response['status']}")
        if 'user_id' in response:
            print(f"User ID: {response['user_id']}")
        return
    
    # Interactive mode
    print("\nEnter 'exit' to quit.")
    while True:
        user_input = input("\nYou: ")
        
        if user_input.lower() == "exit":
            break
        
        # Show agent activity
        print("\nProcessing...")
        print("  - Perception Agent: Analyzing input...")
        print("  - Orchestration Agent: Planning workflow...")
        
        # Process message
        response = orchestration_agent.process_message(session_id, user_input)
        
        # Show more agent activity
        print("  - Memory Agent: Updating database...")
        print("  - Action Agent: Generating response...")
        
        # Show response
        print(f"\nSystem: {response['message']}")
        
        # Show completion if relevant
        if response["status"] == "completed" and "user_id" in response:
            print(f"\nRegistration completed! User ID: {response['user_id']}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Multi-Agent Registration System")
    parser.add_argument("--cli", action="store_true", help="Run in command line mode")
    parser.add_argument("--message", type=str, help="Process a single message")
    args = parser.parse_args()
    
    # Print banner
    print("""
    ┌─────────────────────────────────────────────────┐
    │                                                 │
    │      MULTI-AGENT REGISTRATION SYSTEM DEMO       │
    │                                                 │
    └─────────────────────────────────────────────────┘
    """)
    
    if args.cli or args.message:
        run_command_line(args)
    else:
        run_chat_interface()

if __name__ == "__main__":
    main()