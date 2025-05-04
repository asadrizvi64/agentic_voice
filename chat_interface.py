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

# For TTS
import pyttsx3

# For STT
import speech_recognition as sr

from agents.orchestration_agent import OrchestrationAgent

class ChatInterface:
    """Chat interface with TTS and STT for the registration system"""
    
    def __init__(self, root):
        """Initialize the chat interface"""
        self.root = root
        self.root.title("Multi-Agent Registration System - Demo")
        self.root.geometry("800x600")
        
        # Initialize the orchestration agent
        self.orchestration_agent = OrchestrationAgent()
        
        # Create session
        self.session_id = self.orchestration_agent.create_session()
        
        # Initialize TTS engine
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 150)
        
        # Initialize STT recognizer
        self.recognizer = sr.Recognizer()
        
        # Message queue
        self.message_queue = queue.Queue()
        
        # Create GUI components
        self._create_widgets()
        
        # Welcome message
        welcome_msg = "Hello! I'm here to help you with your registration. What would you like to do today?"
        self._add_message(welcome_msg, "system")
        self._speak(welcome_msg)
    
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
        
        # Voice input button
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
    
    def _listen(self):
        """Listen for voice input"""
        self.status_var.set("Status: Listening...")
        
        def listen_thread():
            try:
                with sr.Microphone() as source:
                    self.recognizer.adjust_for_ambient_noise(source)
                    audio = self.recognizer.listen(source, timeout=5)
                
                try:
                    text = self.recognizer.recognize_google(audio)
                    self.root.after(0, lambda: self.status_var.set("Status: Processing..."))
                    
                    # Update text input and send
                    self.root.after(0, lambda: self.text_input.insert(0, text))
                    self.root.after(100, self._on_send)
                except sr.UnknownValueError:
                    self.root.after(0, lambda: self.status_var.set("Status: Could not understand audio"))
                except sr.RequestError as e:
                    self.root.after(0, lambda: self.status_var.set(f"Status: Error: {e}"))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"Status: Error: {e}"))
        
        threading.Thread(target=listen_thread, daemon=True).start()
    
    def _speak(self, text):
        """Speak text using TTS"""
        def speak_thread():
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        
        threading.Thread(target=speak_thread, daemon=True).start()
    
    def _add_message(self, message, sender):
        """Add message to chat display"""
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
    
    def _process_messages(self):
        """Process messages in the queue"""
        while True:
            try:
                message = self.message_queue.get(timeout=0.1)
                
                # Update status
                self.root.after(0, lambda: self.status_var.set("Status: Processing..."))
                
                # Show agent activity for perception
                self.root.after(0, lambda msg=message: self._update_agent_activity("perception"))
                
                # Process message
                response = self.orchestration_agent.process_message(self.session_id, message)
                
                # Get a reference to the response for use in lambda functions
                response_ref = response
                
                # Show agent activity for other agents with delays
                self.root.after(500, lambda: self._update_agent_activity("memory"))
                self.root.after(1000, lambda: self._update_agent_activity("action"))
                self.root.after(1500, lambda: self._update_agent_activity("orchestration"))
                
                # Update status
                self.root.after(2000, lambda r=response_ref: self.status_var.set(f"Status: {r['status']}"))
                
                # Show response after slight delay to simulate agent thinking
                self.root.after(2500, lambda r=response_ref: self._add_message(r["message"], "system"))
                
                # Speak response
                self.root.after(2500, lambda r=response_ref: self._speak(r["message"]))
                
                # Mark as done
                self.message_queue.task_done()
                
                # Reset agent activity
                self.root.after(3500, lambda: self._reset_agent_activity())
            except queue.Empty:
                pass
            except Exception as e:
                print(f"Error processing message: {e}")
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
        # Find all agent status labels
        for child in self.root.winfo_children():
            if isinstance(child, ttk.Frame):
                for subchild in child.winfo_children():
                    if isinstance(subchild, ttk.LabelFrame):
                        # Check the text option of the LabelFrame instead of using winfo_text()
                        if subchild.cget("text") == "Agent Status":
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
    
    def _reset_agent_activity(self):
        """Reset all agent activity indicators"""
        # Find all agent status labels
        for child in self.root.winfo_children():
            if isinstance(child, ttk.Frame):
                for subchild in child.winfo_children():
                    if isinstance(subchild, ttk.LabelFrame):
                        # Check the text option of the LabelFrame instead of using winfo_text()
                        if subchild.cget("text") == "Agent Status":
                            for agent_label in subchild.winfo_children():
                                if isinstance(agent_label, ttk.Label):
                                    agent_label.config(foreground="green", font=("Arial", 9, "normal"))
            """Reset all agent activity indicators"""
            # Find all agent status labels
            for child in self.root.winfo_children():
                if isinstance(child, ttk.Frame):
                    for subchild in child.winfo_children():
                        if isinstance(subchild, ttk.LabelFrame) and subchild.winfo_text() == "Agent Status":
                            for agent_label in subchild.winfo_children():
                                if isinstance(agent_label, ttk.Label):
                                    agent_label.config(foreground="green", font=("Arial", 9, "normal"))