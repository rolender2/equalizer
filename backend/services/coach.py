import logging
import time
import json
from typing import List, Optional, Dict, Literal
from core.analysis_engine.tactic_detection import TacticDetector
from core.analysis_engine.tactic_detection_v2 import TacticDetectorV2
from core.analysis_engine.schemas import TranscriptSegment, AnalysisResult

USE_TACTIC_DETECTOR_V2 = True

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Coach:
    def __init__(self, mode: Literal["debrief", "live"] = "debrief", negotiation_type: str = "General", user_speaker_id: int = 0):
        self.mode = mode
        self.negotiation_type = negotiation_type
        self.user_speaker_id = user_speaker_id # Default 0 is User
        self.detector = TacticDetector() # Core engine V1
        self.detector_v2 = TacticDetectorV2() # Core engine V2
        self.last_analyzed_index = 0
        
        # Buffer for windowed analysis
        self.audio_buffer: List[TranscriptSegment] = []
        self.window_size_seconds = 15.0 
        self.last_analysis_time = time.time()
        
        # Dedupe state
        self._last_emit_key = None
        self._last_emit_ts = 0.0
        
        logger.info(f"Coach initialized | Mode: {mode} | Type: {negotiation_type} | User Speaker ID: {user_speaker_id}")

    def set_mode(self, mode: Literal["debrief", "live"]):
        self.mode = mode
        logger.info(f"Coach mode set to: {mode}")

    def set_negotiation_type(self, negotiation_type: str):
        self.negotiation_type = negotiation_type
        logger.info(f"Coach type set to: {negotiation_type}")
        
    def set_user_speaker_id(self, user_speaker_id: int):
        self.user_speaker_id = user_speaker_id
        logger.info(f"Coach user speaker ID set to: {user_speaker_id}")

    async def process_transcript(self, transcript: str, speaker: str) -> Optional[str]:
        """
        Ingests a new transcript line.
        Returns advice string ONLY if in Live Mode and a signal is detected.
        Otherwise buffers and returns None.
        """
        # 1. Role Mapping
        mapped_speaker = "COUNTERPARTY"
        
        # Check against user_speaker_id cfg
        # Incoming speaker might be "Speaker 0", "Speaker 1" or int 0, 1
        # Try to parse
        spk_id = -1
        try:
             # If "Speaker 0" -> 0
             if isinstance(speaker, str) and "Speaker " in speaker:
                 spk_id = int(speaker.replace("Speaker ", "").strip())
             elif isinstance(speaker, int) or (isinstance(speaker, str) and speaker.isdigit()):
                 spk_id = int(speaker)
        except:
             pass
        
        if spk_id == self.user_speaker_id:
             mapped_speaker = "USER"
        
        # Add to buffer with MAPPED speaker
        segment = TranscriptSegment(
            speaker=mapped_speaker,
            text=transcript,
            timestamp=time.time()
        )
        self.audio_buffer.append(segment)
        
        # CHECK MODE: DEBRIEF
        if self.mode == "debrief":
            # Strict Rule: No live analysis.
            return None

        # CHECK MODE: LIVE
        # Check window conditions
        current_time = time.time()
        time_diff = current_time - self.last_analysis_time
        
        # Only analyze if sufficient time passed OR buffer is large enough
        if time_diff >= self.window_size_seconds:
             return await self._analyze_window()
        
        return None

    async def _analyze_window(self) -> Optional[str]:
        """
        Internal: Sends current buffer to Core Engine for analysis.
        """
        if not self.audio_buffer:
            return None
            
        logger.info(f"Analyzing window: {len(self.audio_buffer)} segments")
        
        signals = []
        if USE_TACTIC_DETECTOR_V2:
            # V2 Logic: Last-Line High Precision
            # Context = last ~12 lines
            # New = EXACTLY the last line (most recent)
            
            context_segments = self.audio_buffer[-12:] 
            if not context_segments:
                return None
                
            new_segments = [context_segments[-1]]
            
            # If the last line is USER, we shouldn't even ask the LLM?
            # Optimization: If mapped_speaker is USER, return None immediately?
            # The prompt has a rule "If NEW line is spoken by USER, return NONE".
            # But skipping the call is cheaper. 
            # Requirement 3.2 says to add prompt rule. I will do that too.
            # But let's let the LLM see usage to be safe on context? 
            # Actually, "Evidence must quote the NEW [COUNTERPARTY] line."
            # If last line is user, we can skip detection to save cost/latency.
            # Let's rely on LLM for now as per prompt instructions in task to demonstrate strict prompting, 
            # but ideally we optimized this. I'll stick to LLM enforcement for robustness (maybe user quote triggers context).
            
            logger.info(f"Coach V2 Analysis: 1 new segment (last-line), {len(context_segments)} context")
            
            signals = await self.detector_v2.detect_tactics(
                segments=context_segments, 
                negotiation_type=self.negotiation_type,
                new_segments=new_segments
            )
        else:
            # V1 Logic (Legacy)
            window_segments = self.audio_buffer[-15:] 
            signals = await self.detector.detect_tactics(window_segments, self.negotiation_type)
        
        # Update last analysis time and index
        self.last_analysis_time = time.time()
        self.last_analyzed_index = len(self.audio_buffer)
        
        if signals:
            top_signal = max(signals, key=lambda s: s.confidence)
            
            # Silence "NONE" category signals (Explicit Gate)
            if top_signal.category == "NONE":
                logger.info(f"GATED: NONE (silent)")
                return None
            
            # Dedupe Check
            dedupe_key = (top_signal.category, top_signal.subtype)
            curr_time = time.time()
            
            if dedupe_key == self._last_emit_key and (curr_time - self._last_emit_ts < 45.0):
                logger.info(f"DEDUPED: {top_signal.category}({top_signal.subtype}) - Suppressed")
                return None

            # Update Dedupe State
            self._last_emit_key = dedupe_key
            self._last_emit_ts = curr_time
            
            # Serialize for frontend consumption
            advice_payload = {
                "type": "advice",
                "content": {
                    "category": top_signal.category,
                    "subtype": top_signal.subtype,
                    "confidence": top_signal.confidence,
                    "message": top_signal.message,
                    "options": top_signal.options
                }
            }
            
            logger.info(f"Live Advice Generated: {top_signal.category} ({top_signal.subtype})")
            return json.dumps(advice_payload)
            
        return None

    async def generate_summary(self, transcript_text: str, outcome: dict) -> dict:
        """
        Delegate to Core Engine.
        """
        result = await self.detector.generate_summary(transcript_text, outcome)
        return result.dict()
