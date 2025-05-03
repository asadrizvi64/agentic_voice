# Multi-Agent Registration System

A demonstration of multi-agent architecture for user registration with LangChain and LangGraph, featuring TTS and STT support.

## Overview

This project demonstrates a multi-agent system approach to user registration, where different specialized agents collaborate to process user input and manage the registration workflow.

## Architecture

The system follows a multi-agent architecture with the following components:

### 1. Perception Agent

- Detects user intent (register, update profile, etc.)
- Extracts entities from natural language (name, email, phone, address)
- Analyzes confidence levels for detected intents

### 2. Memory Agent

- Provides persistent storage for user data
- Manages sessions and state
- Retrieves and updates user profiles

### 3. Action Agent

- Executes registration operations
- Validates user information completeness
- Generates natural language responses

### 4. Orchestration Agent

- Coordinates the multi-agent workflow
- Uses LangGraph for state management
- Makes decisions about next steps in the registration process

## Features

- Natural language registration process
- Voice input and output with TTS/STT
- Multi-agent coordination using LangGraph
- Entity extraction from conversation
- Visual agent activity indicators
- Database persistence with SQLite

## Installation

1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements.txt