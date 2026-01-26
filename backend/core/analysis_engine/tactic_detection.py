from openai import AsyncOpenAI
import os
import json
import logging
from typing import List, Optional
from .schemas import TranscriptSegment, TacticSignal, AnalysisResult, ImprovementSummary

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TacticDetector:
    def __init__(self, api_key: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    async def detect_tactics(self, segments: List[TranscriptSegment], negotiation_type: str = "General") -> List[TacticSignal]:
        """
        Analyzes a window of transcripts to detect negotiation tactics.
        Returns a list of detected signals with confidence scores.
        """
        if not segments:
            return []

        # Combine matching speakers to reduce context
        transcript_text = ""
        for seg in segments:
            transcript_text += f"[{seg.speaker}]: {seg.text}\n"

        system_prompt = f"""You are a negotiation intelligence engine (Core Mode).
Context: {negotiation_type} negotiation.

Your Job: Detect if the COUNTERPARTY is using a specific negotiation tactic in the NEWEST segment(s).
Do NOT advise the user. Do NOT script the user. Only DETECT.

PRIORITY RULES:
1. FOCUS ON THE NEWEST SEGMENT. If no new tactic appears there, return category: "NONE".
2. AUTHORITY VS URGENCY:
   - "I don't have authority", "check with manager", "company policy", "no flexibility" -> AUTHORITY (subtype: manager_deferral, policy_shield).
   - ONLY classify as URGENCY if explicit time/scarcity cues exist ("today", "this week", "only one left").
   - If both appear, prioritize the dominant constraint.

Supported Tactics & Subtypes:
- ANCHORING: Setting a high/low opening number.
  Subtypes: numeric_anchor, range_anchor, comparison_anchor
- URGENCY: creating time pressure.
  Subtypes: deadline, scarcity
- AUTHORITY: Claiming lack of authority.
  Subtypes: manager_deferral, policy_shield
- FRAMING: Positioning a loss/gain.
  Subtypes: roi_reframe, monthly_breakdown, minimization
- NONE: No tactic detected.
  Subtype: none

Confidence Threshold:
- Only return options if confidence > 0.7 AND category != "NONE".

Tone Requirements:
- Professional, neutral, and analytical.
- Example: "Pricing Anchor Detected" instead of "They are lowballing you".

Output Schema (JSON):
{{
  "signals": [
    {{
      "category": "ANCHORING | URGENCY | AUTHORITY | FRAMING | NONE",
      "subtype": "string (from list above)",
      "confidence": float (0.0-1.0),
      "evidence": "Quote from transcript causing detection",
      "options": ["One option is to...", "Consider...", "Another approach could be..."],
      "message": "Short neutral observation (e.g. 'Counterparty cited company policy.')"
    }}
  ]
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript_text}
                ],
                max_tokens=300,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            data = json.loads(content)
            
            signals = []
            for item in data.get("signals", []):
                category = item.get("category", "NONE")
                confidence = item.get("confidence", 0)
                
                if category != "NONE" and confidence >= 0.7:
                    # Validate against schema
                    try:
                        # Enforce option limits and prefixes if LLM slipped
                        valid_options = [opt for opt in item.get("options", []) if opt][:3]
                        
                        signal = TacticSignal(
                           category=category,
                           subtype=item.get("subtype", "none"),
                           confidence=confidence,
                           evidence=item.get("evidence", ""),
                           timestamp=segments[-1].timestamp, 
                           options=valid_options, 
                           message=item.get("message", "Signal Detected")
                        )
                        signals.append(signal)
                    except Exception as e:
                        logger.warning(f"Skipping invalid signal item: {item} | Error: {e}")
            
            return signals

        except Exception as e:
            logger.error(f"Error in detect_tactics: {e}")
            return []

    async def generate_summary(self, full_transcript: str, outcome: dict) -> ImprovementSummary:
        """
        Generates the post-session debrief summary.
        """
        # ... logic similar to existing Coach.generate_summary but using pydantic ...
        prompt = f"""Analyze this negotiation.
Outcome: {outcome.get('result', 'unknown')}
Transcript:
{full_transcript[:8000]} # Truncate if too long

Return JSON:
{{
  "strong_move": "Single sentence on what went well",
  "missed_opportunity": "Single sentence on what was missed",
  "improvement_tip": "Single actionable tip"
}}"""

        try:
            response = await self.client.chat.completions.create(
                 model="gpt-4o-mini",
                 messages=[
                     {"role": "system", "content": "You are a strategic negotiation analyst."},
                     {"role": "user", "content": prompt}
                 ],
                 max_tokens=200,
                 temperature=0.6,
                 response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            return ImprovementSummary(
                strong_move=data.get("strong_move", "N/A"),
                missed_opportunity=data.get("missed_opportunity", "N/A"),
                improvement_tip=data.get("improvement_tip", "N/A")
            )
        except Exception as e:
            logger.error(f"Summary generation error: {e}")
            return ImprovementSummary(
                strong_move="Analysis failed",
                missed_opportunity="Analysis failed",
                improvement_tip=str(e)
            )
