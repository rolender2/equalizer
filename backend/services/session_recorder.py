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
    
    def __init__(self, personality: str = "tactical", negotiation_type: str = "General"):
        self.session_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.personality = personality
        self.negotiation_type = negotiation_type
        self.transcripts: list[dict] = []
        self.advice_given: list[dict] = []
        # Outcome data
        self.outcome: Optional[dict] = None
        
        self.session_start = datetime.now().isoformat()
        
        # Create sessions directory in user's documents folder
        self.sessions_dir = self._get_sessions_dir()
        self.session_file = self.sessions_dir / f"{self.session_id}.json"
        
        logger.info(f"Session started: {self.session_id} (Type: {self.negotiation_type})")
        self._save()  # Create initial file
    
    def _get_sessions_dir(self) -> Path:
        """Get or create the sessions directory in the project root."""
        # Resolve project root from this file: backend/services/session_recorder.py -> .../equalizer
        project_root = Path(__file__).resolve().parent.parent.parent
        sessions_dir = project_root / "sessions"
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
    
    def set_outcome(self, result: str, confidence: int, notes: str = ""):
        """
        Set the outcome of the negotiation.
        result: 'won' | 'lost' | 'deferred'
        confidence: 1-5
        negotiation_type: sourced from self.negotiation_type (session context)
        """
        self.outcome = {
            "result": result,
            "confidence": confidence,
            "notes": notes,
            "negotiation_type": self.negotiation_type,
            "timestamp": datetime.now().isoformat()
        }
        self._save()
        logger.info(f"Outcome recorded: {result} (Confidence: {confidence})")

    def _save(self):
        """Save the session to disk."""
        session_data = {
            "session_id": self.session_id,
            "session_start": self.session_start,
            "session_end": datetime.now().isoformat(),
            "personality": self.personality,
            "negotiation_type": self.negotiation_type,
            "transcripts": self.transcripts,
            "advice_given": self.advice_given,
            "outcome": self.outcome,
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

    @staticmethod
    def update_outcome(session_id: str, result: str, confidence: int, notes: str = ""):
        """
        Static method to update outcome for a finished session file.
        Updates outcome with result, confidence, notes.
        Retains negotiation_type from existing file if present, or defaults to "General".
        """
        try:
            # Resolve project root: backend/services/session_recorder.py -> .../equalizer
            project_root = Path(__file__).resolve().parent.parent.parent
            session_path = project_root / "sessions" / f"{session_id}.json"
            
            if not session_path.exists():
                logger.error(f"Session file not found: {session_path}")
                return False

            with open(session_path, 'r') as f:
                data = json.load(f)
            
            # Source negotiation_type from session context (file data), or default
            negotiation_type = data.get("negotiation_type", "General")

            data["outcome"] = {
                "result": result,
                "confidence": confidence,
                "notes": notes,
                "negotiation_type": negotiation_type,
                "timestamp": datetime.now().isoformat()
            }
            
            with open(session_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Outcome updated for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating outcome for {session_id}: {e}")
            return False

    @staticmethod
    def list_sessions() -> list[dict]:
        """
        List all recorded sessions with summary metadata.
        Returns list sorted by date descending (newest first).
        """
        try:
            # Resolve project root: backend/services/session_recorder.py -> .../equalizer
            project_root = Path(__file__).resolve().parent.parent.parent
            sessions_dir = project_root / "sessions"
            
            if not sessions_dir.exists():
                return []
                
            sessions = []
            for file_path in sessions_dir.glob("*.json"):
                try:
                    with open(file_path, 'r') as f:
                        # Read minimal data to avoid memory bloat
                        # For very large history, we might want to optimize this to not read full files
                        data = json.load(f)
                        
                        summary = {
                            "session_id": data.get("session_id"),
                            "timestamp": data.get("session_start"),
                            "negotiation_type": data.get("negotiation_type", "General"),
                            "negotiation_score": (data.get("reflection") or {}).get("negotiation_score", 0),
                            "outcome": (data.get("outcome") or {}).get("result"),
                            "duration_seconds": 0 
                        }
                        
                        # Calculate duration roughly
                        start = data.get("session_start")
                        end = data.get("session_end")
                        if start and end:
                            try:
                                s_dt = datetime.fromisoformat(start)
                                e_dt = datetime.fromisoformat(end)
                                summary["duration_seconds"] = int((e_dt - s_dt).total_seconds())
                            except:
                                pass
                                
                        sessions.append(summary)
                except Exception as e:
                    logger.warning(f"Error parse session file {file_path}: {e}")
                    continue
            
            # Sort by timestamp desc
            sessions.sort(key=lambda x: x["timestamp"] or "", reverse=True)
            return sessions
            
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []

    @staticmethod
    def get_session(session_id: str) -> Optional[dict]:
        """Retrieve full session data by ID."""
        try:
            # Resolve project root
            project_root = Path(__file__).resolve().parent.parent.parent
            session_file = project_root / "sessions" / f"{session_id}.json"
            
            if not session_file.exists():
                return None
                
            with open(session_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {e}")
            return None

    @staticmethod
    def swap_speaker_role(session_id: str, transcript_index: int) -> bool:
        """
        Swap the speaker role for a specific transcript entry.
        Arguments:
            session_id: The ID of the session
            transcript_index: The index in the 'transcripts' array to swap
        """
        try:
            project_root = Path(__file__).resolve().parent.parent.parent
            session_file = project_root / "sessions" / f"{session_id}.json"
            
            if not session_file.exists():
                logger.error(f"Session {session_id} not found")
                return False
                
            with open(session_file, 'r') as f:
                data = json.load(f)
                
            transcripts = data.get("transcripts", [])
            if transcript_index < 0 or transcript_index >= len(transcripts):
                logger.error(f"Index {transcript_index} out of bounds for session {session_id}")
                return False
                
            # Toggle logic
            current_speaker = str(transcripts[transcript_index].get("speaker", "unknown"))
            # If it's currently 'user' (or 'you'), swap to 'counterparty' (or 'them') and vice versa
            # We standardize on 'user' vs 'counterparty' for storage, but handle 'unknown'
            
            new_speaker = "counterparty"
            if current_speaker.lower() in ["counterparty", "speaker 1", "1"]:
                new_speaker = "user"
            elif current_speaker.lower() in ["user", "speaker 0", "you", "0"]:
                new_speaker = "counterparty"
            else:
                # Default unknown -> user (safest bet usually, or maybe toggle to counterparty? let's loop)
                new_speaker = "user"
                
            transcripts[transcript_index]["speaker"] = new_speaker
            data["transcripts"] = transcripts
            
            with open(session_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            return True
        except Exception as e:
            logger.error(f"Error swapping speaker for {session_id}: {e}")
            return False
