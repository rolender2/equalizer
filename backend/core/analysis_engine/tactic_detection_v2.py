from openai import AsyncOpenAI
import os
import json
import logging
from typing import List, Optional
from .schemas import TranscriptSegment, TacticSignal, AnalysisResult, ImprovementSummary

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TacticDetectorV2:
    def __init__(self, api_key: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    async def detect_tactics(self, segments: List[TranscriptSegment], negotiation_type: str = "General", new_segments: Optional[List[TranscriptSegment]] = None, context_limit: int = 12) -> List[TacticSignal]:
        """
        Analyzes a window of transcripts to detect negotiation tactics.
        Returns a list of detected signals with confidence scores.
        """
        # If new_segments not provided (legacy call), treat all segments as new? 
        # Or better, if caller doesn't separate, we just take the last few as new?
        # The prompt requires strict separation.
        # Requirement: "Classify tactics in NEW only. CONTEXT is background only"
        
        if not segments and not new_segments:
            return []

        # Prepare Context Text
        context_text = ""
        # segments acts as context if new_segments is passed. 
        # If new_segments is passed, 'segments' arg is treated as context.
        # We limit context to last `context_limit` items.
        
        ctx_segs = segments[-context_limit:] if segments else []
        for seg in ctx_segs:
            context_text += f"[{seg.speaker}]: {seg.text}\n"

        # Prepare New Text
        new_text = ""
        target_segments = new_segments if new_segments else []
        
        # Fallback: if new_segments is None/Empty but segments has data, 
        # AND this is a V2 call where we might have just passed everything in 'segments'?
        # The requirement says explicitly: "Explicitly separate CONTEXT and NEW in the prompt"
        # Ideally the caller (Coach) separates them.
        # If target_segments is empty, we have nothing to detect on.
        
        if not target_segments:
            # If no new segments to analyze, return empty
            return []

        for seg in target_segments:
            new_text += f"[{seg.speaker}]: {seg.text}\n"
            
        system_prompt = f"""You are a negotiation intelligence engine (Core Mode).
Context: {negotiation_type} negotiation.

Your Job: Detect if the COUNTERPARTY is using a specific negotiation tactic in the NEW SECTIONS only.
Use the CONTEXT for background understanding but DO NOT classify based on it.

HARD RULES:
- Only detect tactics if the NEW line is spoken by [COUNTERPARTY].
- If the NEW line is spoken by [USER], return category "NONE".
- Evidence must quote the NEW [COUNTERPARTY] line.
- You are assisting the USER (the negotiator using this tool), not the counterparty.
- Options must help the user slow pace, verify claims, surface decision makers, protect leverage, or re-anchor with data.
- Never produce options that increase urgency, amplify pressure, or help the counterparty close.

Forbidden option intent examples: 'emphasize the benefits of acting quickly', 'highlight urgency', 'push them to sign', 'close the deal', 'sell the value'.

PRIORITY RULES:
1. FOCUS ON THE NEW SECTONS. If no new tactic appears there, return category: "NONE".
2. AUTHORITY VS URGENCY:
   - "I don't have authority", "check with manager", "company policy", "no flexibility" -> AUTHORITY (subtype: manager_deferral, policy_shield).
   - ONLY classify as URGENCY if explicit time/scarcity cues exist ("today", "this week", "only one left").
   - If both appear, prioritize the dominant constraint in the NEW SECTONS.
   - If the detected tactic is URGENCY, options should focus on pausing, verifying deadlines, requesting time, or exploring alternatives — not acting faster.

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

Options Guidelines:
- Must be 0-3 options.
- Start with: "One option is to...", "Consider...", "Another approach could be...".
- If confidence < 0.7 or category == "NONE", return empty options.

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

        user_content = f"""PASSED CONTEXT (Do not classify this):
{context_text}

NEW SECTIONS (Classify this):
{new_text}
"""

        async def attempt_parse(content_raw):
            try:
                return json.loads(content_raw)
            except json.JSONDecodeError:
                # Simple repair: try to find the JSON object subset
                try:
                    start = content_raw.find("{")
                    end = content_raw.rfind("}") + 1
                    if start != -1 and end != -1:
                        return json.loads(content_raw[start:end])
                except:
                    pass
                return None

        # Banned Phrases Filter (Case-Insensitive)
        BANNED_PHRASES = [
            # Seller-ish closing language
            "emphasize the benefits", "highlight urgency", "create urgency", 
            "act quickly", "move fast", "close", "push", "pressure", 
            "sell", "overcome objections", "convince", "increase urgency", 
            "secure the offer",
            # Seller role language (Buyer-side framing)
            "your offering", "your service", "value proposition", 
            "justify your pricing", "your pricing"
        ]

        def filter_options(raw_opts):
            clean_opts = []
            for opt in raw_opts:
                if not any(banned in opt.lower() for banned in BANNED_PHRASES):
                    clean_opts.append(opt)
            return clean_opts

        data = None
        # First Attempt
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                max_tokens=300,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            data = await attempt_parse(response.choices[0].message.content.strip())
        except Exception as e:
            logger.error(f"V2 Detection Error (Attempt 1): {e}")

        # Retry logic (JSON failure OR Filtered Empty)
        retry_needed = False
        retry_prompt_suffix = ""

        if data is None:
            retry_needed = True
            retry_prompt_suffix = "\nIMPORTANT: RETURN VALID JSON ONLY."
        else:
            # Check if we need to retry due to over-filtering
            # If we have a signal > 0.7 but all options were filtered out
            signals_check = data.get("signals", [])
            if signals_check:
                item = signals_check[0] # Assuming single signal focus for update
                cat = item.get("category", "NONE")
                conf = item.get("confidence", 0)
                raw_opts = item.get("options", [])
                
                if cat != "NONE" and conf >= 0.7 and raw_opts:
                    clean_opts = filter_options(raw_opts)
                    if not clean_opts: # All filtered out!
                        retry_needed = True
                        retry_prompt_suffix = "\nIMPORTANT: Options must be user-protective (slow pace / verify / regain control). Do not include seller coaching."
                        logger.info(f"V2 Retry triggered: All options filtered for {cat}. Retrying with strict instruction.")

        if retry_needed:
            # logger.warning("V2 JSON Parse failed or Options Filtered, retrying once...") # redundant with specific log above
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt + retry_prompt_suffix},
                        {"role": "user", "content": user_content}
                    ],
                    max_tokens=300,
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )
                data = await attempt_parse(response.choices[0].message.content.strip())
            except Exception as e:
                logger.error(f"V2 Detection Error (Attempt 2): {e}")

        if data is None:
            return []

        signals = []
        for item in data.get("signals", []):
            try:
                category = item.get("category", "NONE")
                confidence = item.get("confidence", 0)
                
                # Enforce Options Logic
                raw_options = item.get("options", [])
                
                # Apply Filter
                filtered_options = filter_options(raw_options)
                
                valid_options = []
                
                if category != "NONE" and confidence >= 0.7:
                    allowed_prefixes = ["One option is to", "Consider", "Another approach could be", "You might"] # Added "You might" to align with frontend
                    # Strict prefix enforcement of filtered options
                    for opt in filtered_options:
                        if len(valid_options) >= 3:
                            break
                        
                        # Check prefix
                        detected_prefix = next((p for p in allowed_prefixes if opt.startswith(p)), None)
                        
                        if detected_prefix:
                            valid_options.append(opt)
                        else:
                             # Auto-fix prefix
                             valid_options.append(f"Consider {opt[0].lower() + opt[1:]}")
                
                # Check bounds
                if len(valid_options) > 3:
                    valid_options = valid_options[:3]

                signal = TacticSignal(
                   category=category,
                   subtype=item.get("subtype", "none"),
                   confidence=confidence,
                   evidence=item.get("evidence", ""),
                   timestamp=target_segments[-1].timestamp, 
                   options=valid_options, 
                   message=item.get("message", "Signal Detected")
                )
                signals.append(signal)
            except Exception as e:
                logger.warning(f"V2 Skipping invalid signal item: {item} | Error: {e}")

        return signals

    async def generate_summary(self, full_transcript: str, outcome: dict) -> ImprovementSummary:
        """
        Generates the post-session debrief summary.
        Refers to v1 logic or similar implementation.
        """
        # We can copy the exact logic from V1 since "Do not change ImprovementSummary behavior" is a req.
        # Repeating the code here to be self-contained.
        
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
