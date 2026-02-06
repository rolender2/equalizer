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
        
        # Test Mode Logic
        self.test_mode_counterparty = False
        
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

    def set_test_mode_counterparty(self, val: bool):
        self.test_mode_counterparty = bool(val)
        logger.info(f"Coach test_mode_counterparty set to: {self.test_mode_counterparty}")

    def _speaker_id_from_segment(self, seg_speaker) -> int:
        """
        Normalized speaker identity to int if possible.
        Supports int speaker_id, 'Speaker N', 'N'.
        Returns -1 if unknown/unparseable.
        Returns -2 if already mapped to USER/COUNTERPARTY (legacy safety).
        """
        if isinstance(seg_speaker, int):
            return seg_speaker
            
        if isinstance(seg_speaker, str):
            if seg_speaker in ("USER", "COUNTERPARTY"):
                return -2
            
            # handle "Speaker 0" / "speaker 0"
            import re
            m = re.search(r"(\d+)", seg_speaker)
            if m:
                return int(m.group(1))
                
        return -1

    def _role_label(self, speaker_input) -> str:
        """
        Map speaker input to USER or COUNTERPARTY based on user_speaker_id.
        """
        # 1. Check if already mapped (safety)
        if isinstance(speaker_input, str) and speaker_input in ("USER", "COUNTERPARTY"):
            return speaker_input
            
        # 2. Extract ID
        spk_id = self._speaker_id_from_segment(speaker_input)
        
        # 3. Map
        if spk_id == -2: # Already mapped signal
            return speaker_input # Should have contributed to spk_id extraction check above, but for safety
            
        if spk_id == self.user_speaker_id:
            return "USER"
            
        # Default all others to COUNTERPARTY
        return "COUNTERPARTY"

    async def process_transcript(self, transcript: str, speaker: str | int) -> Optional[str]:
        """
        Ingests a new transcript line.
        Returns advice string ONLY if in Live Mode and a signal is detected.
        Otherwise buffers and returns None.
        """
        # Map Role properly
        mapped_role = self._role_label(speaker)
        if self.test_mode_counterparty:
            mapped_role = "COUNTERPARTY"
        
        # Add to buffer with MAPPED speaker
        segment = TranscriptSegment(
            speaker=mapped_role,
            text=transcript,
            timestamp=time.time()
        )
        self.audio_buffer.append(segment)
        
        # Log for verification
        # Only log if it's a new interaction type or periodically could be noisy, 
        # but User requested explicit log confirming role.
        # We'll log the LAST segment's role behavior in _analyze_window mostly, 
        # but let's log here for immediate feedback as requested ("NEW role=...").
        # To avoid spam, maybe debug level, but request said "Add an explicit log...".
        # Let's log info.
        tm_str = " (TEST_MODE)" if self.test_mode_counterparty else ""
        logger.info(f"NEW role={mapped_role}{tm_str} spk_input={speaker} text=\"{transcript[:30]}...\"")

        
        # CHECK MODE: DEBRIEF
        if self.mode == "debrief":
            # Strict Rule: No live analysis.
            return None

        # CHECK MODE: LIVE
        # Check window conditions
        current_time = time.time()
        time_diff = current_time - self.last_analysis_time
        
        # Only analyze if sufficient time passed OR this is the first eligible segment
        if time_diff >= self.window_size_seconds or self.last_analyzed_index == 0:
             return await self._analyze_window()
        
        return None

    async def _analyze_window(self) -> Optional[str]:
        """
        Internal: Sends current buffer to Core Engine for analysis.
        """
        if not self.audio_buffer:
            return None
            
        logger.info(f"Analyzing window: {len(self.audio_buffer)} segments")

        newest_segment = self.audio_buffer[-1]
        if not self.test_mode_counterparty and newest_segment.speaker != "COUNTERPARTY":
            logger.info("GATED: newest segment is USER (no analysis)")
            return None
        
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
            
            # Serialize for frontend consumption (v3 payload)
            advice_payload = {
                "category": top_signal.category,
                "subtype": top_signal.subtype,
                "confidence": top_signal.confidence,
                "headline": top_signal.headline,
                "why": top_signal.why,
                "best_question": top_signal.best_question,
                "options": top_signal.options,
                "evidence": top_signal.evidence,
                "timestamp": top_signal.timestamp
            }
            
            logger.info(f"Live Advice Generated: {top_signal.category} ({top_signal.subtype})")
            return advice_payload
            
        return None

    async def generate_summary(self, transcript_text: str, outcome: dict, expanded: bool = False) -> dict:
        """
        Delegate to Core Engine.
        """
        if USE_TACTIC_DETECTOR_V2:
             # Pass the current coach context (e.g. 'Renewal', 'Vendor Pricing') to the engine
             result = await self.detector_v2.generate_summary(
                 transcript_text, 
                 outcome, 
                 user_speaker_id=self.user_speaker_id,
                 negotiation_type=self.coach_type
             )
             return result.dict()
        else:
             result = await self.detector.generate_summary(transcript_text, outcome, expanded=expanded)
             return result.dict()
