#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple database implementation for user registration prototype
"""

import json
import os
import sqlite3
from typing import Dict, Any, Optional
import uuid
from datetime import datetime, timedelta

class SimpleDB:
    """Simple database for user registration"""
    
    def __init__(self, db_path="user_data.db"):
        """Initialize the database"""
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create user table
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
    
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user"""
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
    
    def get_user(self, user_id=None, email=None):
        """Get a user by ID or email"""
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
    
    def create_session(self):
        """Create a new session"""
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
    
    def update_session(self, session_id, data):
        """Update session data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE sessions SET data = ? WHERE session_id = ?",
            (json.dumps(data), session_id)
        )
        
        conn.commit()
        conn.close()
    
    def get_session(self, session_id):
        """Get session data"""
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