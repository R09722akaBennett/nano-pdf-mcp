import os
import shutil
import uuid
import json
from typing import List, Optional
from pydantic import BaseModel

class SessionState(BaseModel):
    original_path: str
    current_path: str
    history: List[str]
    current_index: int

class HistoryManager:
    """Manages session state and PDF version history locally."""
    def __init__(self, base_dir: Optional[str] = None):
        """Initializes the history manager with a base directory for session data."""
        # Use project's output directory instead of home directory
        if not base_dir:
            # Get the directory where this script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Create output directory in the project root
            base_dir = os.path.join(script_dir, "output")
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.sessions_dir = os.path.join(self.base_dir, "sessions")
        os.makedirs(self.sessions_dir, exist_ok=True)

    def _get_session_dir(self, session_id: str) -> str:
        """Returns the directory path for a specific session."""
        sdir = os.path.join(self.sessions_dir, session_id)
        os.makedirs(sdir, exist_ok=True)
        return sdir

    def init_session(self, pdf_path: str) -> str:
        """Initializes a new session by copying the original PDF."""
        session_id = str(uuid.uuid4())
        sdir = self._get_session_dir(session_id)
        
        # Copy initial PDF to session dir
        v0_path = os.path.join(sdir, "v0_initial.pdf")
        shutil.copy2(pdf_path, v0_path)
        
        state = SessionState(
            original_path=pdf_path,
            current_path=v0_path,
            history=[v0_path],
            current_index=0
        )
        
        self.save_state(session_id, state)
        return session_id

    def save_state(self, session_id: str, state: SessionState):
        """Persists the session state to a JSON file."""
        sdir = self._get_session_dir(session_id)
        with open(os.path.join(sdir, "state.json"), "w", encoding="utf-8") as f:
            f.write(state.model_dump_json())

    def load_state(self, session_id: str) -> SessionState:
        """Loads the session state from a JSON file."""
        sdir = self._get_session_dir(session_id)
        state_path = os.path.join(sdir, "state.json")
        if not os.path.exists(state_path):
            raise FileNotFoundError(f"Session {session_id} not found")
        with open(state_path, "r", encoding="utf-8") as f:
            return SessionState.model_validate_json(f.read())

    def add_version(self, session_id: str, new_pdf_path: str) -> SessionState:
        """Adds a new PDF version to the session history."""
        state = self.load_state(session_id)
        sdir = self._get_session_dir(session_id)
        
        # Move new file to session dir
        version_id = f"v{len(state.history)}_{uuid.uuid4().hex[:8]}.pdf"
        final_path = os.path.join(sdir, version_id)
        shutil.move(new_pdf_path, final_path)
        
        # Truncate forward history
        state.history = state.history[:state.current_index + 1]
        state.history.append(final_path)
        state.current_index = len(state.history) - 1
        state.current_path = final_path
        
        self.save_state(session_id, state)
        return state

    def undo(self, session_id: str) -> SessionState:
        """Reverts to the previous PDF version in history."""
        state = self.load_state(session_id)
        if state.current_index > 0:
            state.current_index -= 1
            state.current_path = state.history[state.current_index]
            self.save_state(session_id, state)
        return state

    def redo(self, session_id: str) -> SessionState:
        """Advances to the next PDF version in history."""
        state = self.load_state(session_id)
        if state.current_index < len(state.history) - 1:
            state.current_index += 1
            state.current_path = state.history[state.current_index]
            self.save_state(session_id, state)
        return state
    
    def commit(self, session_id: str, output_path: Optional[str] = None):
        """Copies the current version to the original or specified export path."""
        state = self.load_state(session_id)
        dest = output_path if output_path else state.original_path
        shutil.copy2(state.current_path, dest)
        return dest
