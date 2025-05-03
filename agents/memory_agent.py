#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Memory Agent
----------
Responsible for data persistence and retrieval.
"""

import json
import sqlite3
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

class MemoryAgent:
    """Agent responsible for data persistence."""
    
    def __init__(self, db_path="user_data.db"):
        """
        Initialize the memory agent.
        
        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT UNIQUE,
            phone TEXT,
            address TEXT,
            password_hash TEXT,
            created_at TEXT
        )
        ''')
        
        # Create sessions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            data TEXT,
            created_at TEXT
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def store_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store user data in the database.
        
        Args:
            user_data: User profile data
            
        Returns:
            Result of the operation
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if email exists
        if 'email' in user_data:
            cursor.execute("SELECT user_id FROM users WHERE email = ?", (user_data.get('email'),))
            if cursor.fetchone():
                conn.close()
                return {"status": "error", "message": "Email already exists"}
        
        # Create user
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        
        cursor.execute(
            "INSERT INTO users (user_id, name, email, phone, address, password_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                user_id,
                user_data.get('name'),
                user_data.get('email'),
                user_data.get('phone'),
                user_data.get('address'),
                user_data.get('password', ''),  # Simple storage for prototype
                now
            )
        )
        
        conn.commit()
        conn.close()
        
        return {"status": "success", "user_id": user_id, "message": "User created successfully"}
    
    def retrieve_user(self, user_id=None, email=None) -> Optional[Dict[str, Any]]:
        """
        Retrieve user data from the database.
        
        Args:
            user_id: User ID
            email: User email
            
        Returns:
            User data or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        elif email:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        else:
            conn.close()
            return None
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def create_session(self) -> str:
        """
        Create a new session.
        
        Returns:
            Session ID
        """
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO sessions (session_id, user_id, data, created_at) VALUES (?, ?, ?, ?)",
            (session_id, None, "{}", now)
        )
        
        conn.commit()
        conn.close()
        
        return session_id
    
    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Update session data.
        
        Args:
            session_id: Session ID
            data: Session data
            
        Returns:
            Success status
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE sessions SET data = ? WHERE session_id = ?",
            (json.dumps(data), session_id)
        )
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def retrieve_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            data = dict(row)
            try:
                data['data'] = json.loads(data['data'])
            except:
                data['data'] = {}
            return data
        return None