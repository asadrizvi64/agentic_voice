#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Chat interface with TTS and STT for the registration system
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import time
import os
import logging
from typing import Dict, Any, List, Optional
from agents.orchestration_agent import OrchestrationAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# For TTS
try:
    import pyttsx3
except ImportError:
    logger.warning("pyttsx3 not found. Text-to-speech will be disabled.")
    pyttsx3 = None

# For STT
try:
    import speech_recognition as sr
except ImportError:
    logger.warning("speech_recognition not found. Speech-to-text will be disabled.")
    sr = None


class ChatInterface:
    """Chat interface with TTS and STT for the registration system"""
    
    def __init__(self, root):
        """Initialize the chat interface"""
        self.root = root
        self.root.title("Multi-Agent Registration System - Demo")
        self.root.geometry("800x600")
        
        logger.info("Initializing chat interface")
        
        # Initialize the orchestration agent
        try:
            self.orchestration_agent = OrchestrationAgent()
            
            # Create session
            self.session_id = self.orchestration_agent.create_session()
            logger.info(f"Created session: {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to initialize orchestration agent: {e}")
            self.show_error(f"Failed to initialize: {str(e)}")
            return
        
        # Initialize TTS engine
        if pyttsx3:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 150)
                logger.info("TTS engine initialized")
            except Exception as e:
                logger.error(f"Failed to initialize TTS engine: {e}")
                self.tts_engine = None
        else:
            self.tts_engine = None
        
        # Initialize STT recognizer
        if sr:
            try:
                self.recognizer = sr.Recognizer()
                logger.info("STT recognizer initialized")
            except Exception as e:
                logger.error(f"Failed to initialize STT recognizer: {e}")
                self.recognizer = None
        else:
            self.recognizer = None
        
        # Message queue
        self.message_queue = queue.Queue()
        
        # Create GUI components
        self._create_widgets()
        
        # Welcome message
        welcome_msg = "Hello! I'm here to help you with your registration. What would you like to do today?"
        self._add_message(welcome_msg, "system")
        if self.tts_engine:
            self._speak(welcome_msg)
    
    def show_error(self, message):
        """Show error message in a popup"""
        error_window = tk.Toplevel(self.root)
        error_window.title("Error")
        error_label = ttk.Label(error_window, text=message, wraplength=300)
        error_label.pack(padx=20, pady=20)
        ok_button = ttk.Button(error_window, text="OK", command=error_window.destroy)
        ok_button.pack(pady=(0, 10))
    
    def _create_widgets(self):
        """Create GUI widgets"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title label
        title_label = ttk.Label(main_frame, text="Multi-Agent Registration System", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Agent status frame
        agent_frame = ttk.LabelFrame(main_frame, text="Agent Status")
        agent_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Agent status indicators
        perception_status = ttk.Label(agent_frame, text="Perception Agent: Active", foreground="green")
        perception_status.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        memory_status = ttk.Label(agent_frame, text="Memory Agent: Active", foreground="green")
        memory_status.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        action_status = ttk.Label(agent_frame, text="Action Agent: Active", foreground="green")
        action_status.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        orchestration_status = ttk.Label(agent_frame, text="Orchestration Agent: Active", foreground="green")
        orchestration_status.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        # Chat display
        self.chat_display = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Input frame
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Text input
        self.text_input = ttk.Entry(input_frame, width=50)
        self.text_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.text_input.bind("<Return>", self._on_send)
        
        # Send button
        send_button = ttk.Button(input_frame, text="Send", command=self._on_send)
        send_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Voice input button (only if sr is available)
        if self.recognizer:
            voice_button = ttk.Button(input_frame, text="🎤", width=3, command=self._listen)
            voice_button.pack(side=tk.LEFT)
        
        # Status frame
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Status label
        self.status_var = tk.StringVar(value="Status: Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT)
        
        # Set focus to input
        self.text_input.focus_set()
        
        # Start message processing thread
        threading.Thread(target=self._process_messages, daemon=True).start()
    
    def _on_send(self, event=None):
        """Handle send button click or Enter key"""
        message = self.text_input.get().strip()
        if message:
            self.text_input.delete(0, tk.END)
            self._add_message(message, "user")
            
            # Add to message queue
            self.message_queue.put(message)
            logger.info(f"Added message to queue: {message[:30]}...")
    
    def _listen(self):
        """Listen for voice input"""
        if not self.recognizer:
            self.status_var.set("Status: Speech recognition not available")
            return
            
        self.status_var.set("Status: Listening...")
        logger.info("Started listening for voice input")
        
        def listen_thread():
            try:
                with sr.Microphone() as source:
                    self.recognizer.adjust_for_ambient_noise(source)
                    audio = self.recognizer.listen(source, timeout=5)
                
                try:
                    text = self.recognizer.recognize_google(audio)
                    logger.info(f"Recognized speech: {text}")
                    self.root.after(0, lambda: self.status_var.set("Status: Processing..."))
                    
                    # Update text input and send
                    self.root.after(0, lambda: self.text_input.insert(0, text))
                    self.root.after(100, self._on_send)
                except sr.UnknownValueError:
                    logger.warning("Could not understand audio")
                    self.root.after(0, lambda: self.status_var.set("Status: Could not understand audio"))
                except sr.RequestError as e:
                    logger.error(f"Error in speech recognition request: {e}")
                    self.root.after(0, lambda: self.status_var.set(f"Status: Error: {e}"))
            except Exception as e:
                logger.error(f"Error in speech recognition: {e}")
                self.root.after(0, lambda: self.status_var.set(f"Status: Error: {e}"))
        
        threading.Thread(target=listen_thread, daemon=True).start()
    
    def _speak(self, text):
        """Speak text using TTS"""
        if not self.tts_engine:
            logger.warning("TTS engine not available")
            return
            
        def speak_thread():
            try:
                logger.info(f"Speaking: {text[:30]}...")
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception as e:
                logger.error(f"Error in TTS: {e}")
        
        threading.Thread(target=speak_thread, daemon=True).start()
    
    def _add_message(self, message, sender):
        """Add message to chat display"""
        try:
            self.chat_display.config(state=tk.NORMAL)
            
            if sender == "user":
                self.chat_display.insert(tk.END, "You: ", "user_tag")
                self.chat_display.tag_configure("user_tag", foreground="blue", font=("Arial", 10, "bold"))
            else:
                self.chat_display.insert(tk.END, "System: ", "system_tag")
                self.chat_display.tag_configure("system_tag", foreground="green", font=("Arial", 10, "bold"))
            
            self.chat_display.insert(tk.END, f"{message}\n\n")
            self.chat_display.see(tk.END)
            self.chat_display.config(state=tk.DISABLED)
        except Exception as e:
            logger.error(f"Error adding message to display: {e}")
    
    def _process_messages(self):
        """Process messages in the queue"""
        while True:
            try:
                message = self.message_queue.get(timeout=0.1)
                logger.info(f"Processing message from queue: {message[:30]}...")
                
                # Update status
                self.root.after(0, lambda: self.status_var.set("Status: Processing..."))
                
                # Show agent activity
                self.root.after(0, lambda: self._update_agent_activity("perception"))
                
                try:
                    # Process message with error handling
                    response = self.orchestration_agent.process_message(self.session_id, message)
                    
                    # Save response for lambda functions
                    resp = response.copy() if hasattr(response, 'copy') else response
                    
                    # Show agent activity
                    self.root.after(500, lambda: self._update_agent_activity("memory"))
                    self.root.after(1000, lambda: self._update_agent_activity("action"))
                    self.root.after(1500, lambda: self._update_agent_activity("orchestration"))
                    
                    # Update status
                    self.root.after(2000, lambda r=resp: self.status_var.set(f"Status: {r['status']}"))
                    
                    # Show response after slight delay to simulate agent thinking
                    self.root.after(2500, lambda r=resp: self._add_message(r["message"], "system"))
                    
                    # Speak response
                    if self.tts_engine:
                        self.root.after(2500, lambda r=resp: self._speak(r["message"]))
                except Exception as e:
                    # Handle error in orchestration
                    error_msg = f"Sorry, there was an error processing your request. Please try again."
                    logger.error(f"Error in orchestration: {e}")
                    self.root.after(0, lambda: self._add_message(error_msg, "system"))
                    if self.tts_engine:
                        self.root.after(0, lambda: self._speak(error_msg))
                    self.root.after(0, lambda: self.status_var.set(f"Status: Error"))
                    import traceback
                    traceback.print_exc()
                
                # Mark as done
                self.message_queue.task_done()
                
                # Reset agent activity
                self.root.after(3500, lambda: self._reset_agent_activity())
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                import traceback
                traceback.print_exc()
                self.root.after(0, lambda: self.status_var.set(f"Status: Error: {e}"))
                try:
                    self.message_queue.task_done()
                except:
                    pass
                
                time.sleep(0.1)
    
    def _update_agent_activity(self, agent_type):
        """Update agent activity indicators"""
        try:
            # Find all agent status labels
            for child in self.root.winfo_children():
                if isinstance(child, ttk.Frame):
                    for subchild in child.winfo_children():
                        if isinstance(subchild, ttk.LabelFrame) and subchild.cget("text") == "Agent Status":
                            for agent_label in subchild.winfo_children():
                                if isinstance(agent_label, ttk.Label):
                                    label_text = agent_label.cget("text").lower()
                                    if agent_type == "perception" and "perception" in label_text:
                                        agent_label.config(foreground="red", font=("Arial", 9, "bold"))
                                    elif agent_type == "memory" and "memory" in label_text:
                                        agent_label.config(foreground="red", font=("Arial", 9, "bold"))
                                    elif agent_type == "action" and "action" in label_text:
                                        agent_label.config(foreground="red", font=("Arial", 9, "bold"))
                                    elif agent_type == "orchestration" and "orchestration" in label_text:
                                        agent_label.config(foreground="red", font=("Arial", 9, "bold"))
        except Exception as e:
            logger.error(f"Error updating agent activity: {e}")
    
    def _reset_agent_activity(self):
        """Reset all agent activity indicators"""
        try:
            # Find all agent status labels
            for child in self.root.winfo_children():
                if isinstance(child, ttk.Frame):
                    for subchild in child.winfo_children():
                        if isinstance(subchild, ttk.LabelFrame) and subchild.cget("text") == "Agent Status":
                            for agent_label in subchild.winfo_children():
                                if isinstance(agent_label, ttk.Label):
                                    agent_label.config(foreground="green", font=("Arial", 9, "normal"))
        except Exception as e:
            logger.error(f"Error resetting agent activity: {e}")