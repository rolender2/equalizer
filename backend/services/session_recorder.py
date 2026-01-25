"""
Session Recorder for Sidekick Equalizer.

Saves transcripts and advice to local JSON files for user review.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SessionRecorder:
    """Records session transcripts and advice to local JSON files."""
    
    def __init__(self, personality: str = "tactical"):
        self.session_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.personality = personality
        self.transcripts: list[dict] = []
        self.advice_given: list[dict] = []
        self.session_start = datetime.now().isoformat()
        
        # Create sessions directory in user's documents folder
        self.sessions_dir = self._get_sessions_dir()
        self.session_file = self.sessions_dir / f"{self.session_id}.json"
        
        logger.info(f"Session started: {self.session_id}")
        self._save()  # Create initial file
    
    def _get_sessions_dir(self) -> Path:
        """Get or create the sessions directory."""
        # Use XDG_DOCUMENTS_DIR on Linux, or fallback to ~/Documents
        documents_dir = os.environ.get(
            "XDG_DOCUMENTS_DIR",
            Path.home() / "Documents"
        )
        sessions_dir = Path(documents_dir) / "Sidekick" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        return sessions_dir
    
    def add_transcript(self, transcript: str, speaker: Optional[str] = None):
        """Add a transcript entry to the session."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "text": transcript,
            "speaker": speaker or "unknown"
        }
        self.transcripts.append(entry)
        self._save()
        logger.debug(f"Transcript added: {transcript[:50]}...")
    
    def add_advice(self, advice: str):
        """Add an advice entry to the session."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "advice": advice,
            "personality": self.personality
        }
        self.advice_given.append(entry)
        self._save()
        logger.debug(f"Advice recorded: {advice}")
    
    def set_personality(self, personality: str):
        """Update the current personality."""
        self.personality = personality
        self._save()
    
    def _save(self):
        """Save the session to disk."""
        session_data = {
            "session_id": self.session_id,
            "session_start": self.session_start,
            "session_end": datetime.now().isoformat(),
            "personality": self.personality,
            "transcripts": self.transcripts,
            "advice_given": self.advice_given,
            "summary": {
                "total_transcripts": len(self.transcripts),
                "total_advice": len(self.advice_given)
            }
        }
        
        try:
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving session: {e}")
    
    def close(self):
        """Finalize and save the session."""
        self._save()
        logger.info(f"Session closed: {self.session_id}")
        logger.info(f"Session file: {self.session_file}")
