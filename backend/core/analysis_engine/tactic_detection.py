from openai import AsyncOpenAI
import os
import json
import logging
import re
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
2. NUMERIC ANCHOR RULE:
   - If the NEWEST segment contains a concrete numeric price/currency amount (e.g., "$50,000", "50k", "USD 50000"),
     classify as ANCHORING with subtype numeric_anchor, unless it is clearly non-negotiation context
     (e.g., "Last year I paid $50,000 for a car").
   - If the NEWEST segment contains a single numeric amount and the speaker is COUNTERPARTY, treat it as an anchor.
3. COMMITMENT TRAP RULE:
   - Only classify COMMITMENT_TRAP when the NEWEST segment is an explicit conditional exchange (e.g., "If I do X, will you do Y?").
   - If there is no clear conditional exchange, do NOT classify COMMITMENT_TRAP.
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

Competitor Mentions:
- If the NEW line references a competitor or "other dealer/offer", classify as ANCHORING (comparison_anchor), not SOCIAL_PROOF.

Confidence Threshold:
- Only return options if confidence > 0.7 AND category != "NONE".

Tone Requirements:
- Professional, neutral, and analytical.
- Example: "Pricing Anchor Detected" instead of "They are lowballing you".

Output Schema (JSON):
{{
  "signals": [
    {{
      "category": "ANCHORING | URGENCY | AUTHORITY | FRAMING | COMMITMENT_TRAP | CONCESSION | BUNDLING | PAYMENT_DEFLECTION | LOSS_AVERSION | SOCIAL_PROOF | NONE",
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
                        if signal.category == "COMMITMENT_TRAP" and not _is_commitment_trap(signal.evidence):
                            continue
                        if signal.category == "SOCIAL_PROOF" and _is_competitor_reference(signal.evidence):
                            signal.category = "ANCHORING"
                            signal.subtype = "comparison_anchor"
                        if signal.category == "SOCIAL_PROOF" and _is_shopping_advice(signal.evidence):
                            continue
                        signals.append(signal)
                    except Exception as e:
                        logger.warning(f"Skipping invalid signal item: {item} | Error: {e}")
            
            # Override: if newest line contains a price amount, emit numeric anchor unless excluded.
            newest_text = segments[-1].text
            if _is_bundling_candidate(newest_text):
                if not signals:
                    return [TacticSignal(
                        category="BUNDLING",
                        subtype="add_on_bundle",
                        confidence=1.0,
                        evidence=newest_text,
                        timestamp=segments[-1].timestamp,
                        options=[],
                        message="Counterparty bundled add-ons into the offer."
                    )]
            if _is_price_anchor_candidate(newest_text):
                if not signals:
                    return [TacticSignal(
                        category="ANCHORING",
                        subtype="numeric_anchor",
                        confidence=1.0,
                        evidence=newest_text,
                        timestamp=segments[-1].timestamp,
                        options=[],
                        message="Counterparty stated a concrete price point."
                    )]

                top = signals[0]
                if top.category == "NONE" or not (top.category == "ANCHORING" and top.subtype in ("numeric_anchor", "range_anchor")):
                    return [TacticSignal(
                        category="ANCHORING",
                        subtype="numeric_anchor",
                        confidence=1.0,
                        evidence=newest_text,
                        timestamp=segments[-1].timestamp,
                        options=[],
                        message="Counterparty stated a concrete price point."
                    )]

            return signals

        except Exception as e:
            logger.error(f"Error in detect_tactics: {e}")
            return []

    async def generate_summary(self, full_transcript: str, outcome: dict, expanded: bool = False) -> ImprovementSummary:
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
  "improvement_tip": "Single actionable tip"{"," if expanded else ""}
  {"" if not expanded else '"expanded_insights": ["3-5 concise bullets on tactics, leverage shifts, and missed opportunities"]'}
}}"""

        def attempt_parse(content_raw):
            try:
                return json.loads(content_raw)
            except json.JSONDecodeError:
                try:
                    start = content_raw.find("{")
                    end = content_raw.rfind("}") + 1
                    if start != -1 and end != -1:
                        return json.loads(content_raw[start:end])
                except Exception:
                    return None
            return None

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
            raw = response.choices[0].message.content
            data = attempt_parse(raw)
            if data is None:
                response = await self.client.chat.completions.create(
                     model="gpt-4o-mini",
                     messages=[
                         {"role": "system", "content": "Return valid JSON only."},
                         {"role": "user", "content": prompt}
                     ],
                     max_tokens=200,
                     temperature=0.0,
                     response_format={"type": "json_object"}
                )
                raw = response.choices[0].message.content
                data = attempt_parse(raw)

            if data is None:
                raise ValueError("Invalid JSON from summary model")

            return ImprovementSummary(
                strong_move=data.get("strong_move", "N/A"),
                missed_opportunity=data.get("missed_opportunity", "N/A"),
                improvement_tip=data.get("improvement_tip", "N/A"),
                expanded_insights=data.get("expanded_insights") if expanded else None
            )
        except Exception as e:
            logger.error(f"Summary generation error: {e}")
            return ImprovementSummary(
                strong_move="Analysis failed",
                missed_opportunity="Analysis failed",
                improvement_tip="Analysis failed"
            )


_AMOUNT_PATTERNS = [
    re.compile(r"\$\s?\d[\d,]*", re.IGNORECASE),
    re.compile(r"\bUSD\s?\d[\d,]*\b", re.IGNORECASE),
    re.compile(r"\b\d+(?:\.\d+)?\s?k\b", re.IGNORECASE),
]

_NON_NEGOTIATION_HINTS = [
    "last year",
    "i paid",
]

_BUNDLING_HINTS = [
    "add-on",
    "add on",
    "bundle",
    "package",
    "included",
    "protection plan",
    "doc fee",
    "documentation fee",
    "processing fee",
    "acting class",
    "acting camp",
    "hair and makeup",
]

_COMPETITOR_HINTS = [
    "competitor",
    "other dealer",
    "another dealer",
    "other dealership",
    "another dealership",
    "their dealer",
    "shopping around",
    "compare",
]

_SHOPPING_ADVICE_HINTS = [
    "call a few people",
    "talk to multiple",
    "talk to other",
    "check other",
    "shop around",
]
def _is_price_anchor_candidate(text: str) -> bool:
    lowered = text.lower()
    if any(hint in lowered for hint in _NON_NEGOTIATION_HINTS):
        return False
    return any(p.search(text) for p in _AMOUNT_PATTERNS)


def _is_competitor_reference(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in _COMPETITOR_HINTS)


def _is_shopping_advice(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in _SHOPPING_ADVICE_HINTS)


def _is_bundling_candidate(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in _BUNDLING_HINTS)


def _is_commitment_trap(text: str) -> bool:
    lowered = text.lower()
    if "if" not in lowered:
        return False
    return any(token in lowered for token in ("will you", "would you", "can you", "could you", "do you", "commit", "sign", "agree"))
