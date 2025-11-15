import sys
from pathlib import Path
import time
from typing import Dict, Optional
from agents.main_agent import ReimbursementManager


class SessionManager:
    """
    Client for managing Claude agent sessions.
    Handles session creation, deletion, message processing, and session listing.
    """
    
    def __init__(self):
        """Initialize the ClaudeClient with an empty sessions dictionary."""
        # Format: {session_id: {"id": str, "created_at": datetime, "manager": ReimbursementManager}}
        self.sessions: Dict[str, dict] = {}
    
    def create_session(self, user_id: str, start_time: int) -> dict:
        """
        Create a new session with a reimbursement manager.
        
        Args:
            user_id: The user/session ID to create
            start_time: Optional datetime for session creation time. If not provided, uses current time.
        
        Returns:
            dict with session_id and created_at timestamp
        
        Raises:
            ValueError: If a session with this ID already exists
        """
        session_id = user_id
        
        # Check if session already exists
        if session_id in self.sessions:
            raise ValueError(f"Session with ID '{session_id}' already exists")
        
        # Use provided start_time or current time
        created_at = start_time if start_time is not None else time.perf_counter()
        
        # Create a new ReimbursementManager instance for this session
        manager = ReimbursementManager(session_id)
        
        # Store the session
        self.sessions[session_id] = {
            "id": session_id,
            "created_at": created_at,
            "manager" : manager
        }
        
        return {
            "session_id": session_id,
            "created_at": start_time
        }
    
    def delete_session(self, user_id: str) -> dict:
        """
        Close and delete a session by its ID.
        
        Args:
            user_id: The user/session ID to delete
        
        Returns:
            dict with success message
        
        Raises:
            ValueError: If the session is not found
        """
        session_id = user_id
        
        if session_id not in self.sessions:
            raise ValueError(f"Session with ID '{session_id}' not found")
        
        # Clean up the session
        # Note: If the manager has any cleanup needed, it should be done here
        del self.sessions[session_id]
        
        return {"message": f"Session {session_id} closed successfully"}
    
    def get_sessions(self) -> dict:
        """
        Fetch all active sessions.
        
        Returns:
            dict with list of sessions containing session_id and created_at
        """
        return {id : {"start_time": self.sessions[id]["created_at"]} for id in self.sessions.keys()}
    
    async def new_dm_message(self, user_id: str, message_content: str, downloaded_file_names) -> dict:
        manager = self.sessions[user_id]["manager"]
        print("manger: ", manager)
        all_info_gathered, response = await manager.process_user_message(message_content, downloaded_file_names)
        return response

    async def new_thread_message(self, user_id: str, message_content: str) -> dict:
        manager = self.sessions[user_id]["manager"]
        response = await manager.read_response(message_content)
        return response