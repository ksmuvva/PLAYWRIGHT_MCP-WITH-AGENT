"""
Code Generation Tools for MCP - Enables recording and generating browser automation scripts.
"""
import asyncio
from typing import Any, Dict, Optional, List

from ..base import PlaywrightBase, logger

class CodeGenSession:
    """Represents a code generation session."""
    def __init__(self, session_id: str, name: str, language: str):
        self.session_id = session_id
        self.name = name
        self.language = language
        self.code = ""
        self.created_at = asyncio.get_event_loop().time()
        self.updated_at = self.created_at
    
    def update(self, code: str):
        """Update the code in the session."""
        self.code = code
        self.updated_at = asyncio.get_event_loop().time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the session to a dictionary."""
        return {
            "session_id": self.session_id,
            "name": self.name,
            "language": self.language,
            "code": self.code,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

class CodeGenerationTools(PlaywrightBase):
    """Tool implementations for code generation."""

    def __init__(self, browser_type: str = "chromium"):
        # Keep cooperative MRO consistent with other tools
        super().__init__(browser_type)
        self.codegen_sessions = {}  # Map of session_id to CodeGenSession
    
    async def start_codegen_session(self, session_name: str, language: str) -> Dict[str, Any]:
        """Start a new code generation session."""
        session_id = f"session_{len(self.codegen_sessions) + 1}"
        session = CodeGenSession(session_id, session_name, language)
        self.codegen_sessions[session_id] = session
        
        return {
            "status": "success",
            "message": f"Code generation session started: {session_name}",
            "session": session.to_dict()
        }

    async def end_codegen_session(self, session_id: str) -> Dict[str, Any]:
        """End a code generation session."""
        if session_id not in self.codegen_sessions:
            return {"status": "error", "message": f"Session not found: {session_id}"}
        
        session = self.codegen_sessions.pop(session_id)
        
        return {
            "status": "success",
            "message": f"Code generation session ended: {session.name}",
            "session": session.to_dict()
        }

    async def get_codegen_session(self, session_id: str) -> Dict[str, Any]:
        """Get the current state of a code generation session."""
        if session_id not in self.codegen_sessions:
            return {"status": "error", "message": f"Session not found: {session_id}"}
        
        session = self.codegen_sessions[session_id]
        
        return {
            "status": "success",
            "session": session.to_dict()
        }

    async def clear_codegen_session(self, session_id: str) -> Dict[str, Any]:
        """Clear a code generation session."""
        if session_id not in self.codegen_sessions:
            return {"status": "error", "message": f"Session not found: {session_id}"}
        
        session = self.codegen_sessions[session_id]
        session.update("")
        
        return {
            "status": "success",
            "message": f"Code generation session cleared: {session.name}",
            "session": session.to_dict()
        }
