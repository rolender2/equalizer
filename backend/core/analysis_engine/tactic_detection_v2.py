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

        newest_text = target_segments[-1].text if target_segments else ""
        if _is_ad_segment(newest_text):
            logger.info("AD FILTER: skipping analysis for ad-like segment")
            return []
            
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
1a. COMMITMENT/TRADES OFF VS URGENCY:
   - Only classify COMMITMENT_TRAP when the NEW line is an explicit conditional exchange ("If I do X, will you do Y?").
   - If there is no clear conditional exchange, do NOT classify COMMITMENT_TRAP.
   - If the NEW line offers a concession in exchange for action ("If I waive X, can you sign now?"), classify as CONCESSION (tradeoff_offer).
   - These take precedence over URGENCY when both appear in the same line.
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
- COMMITMENT_TRAP: Conditional commitment requests.
  Subtypes: conditional_commitment, reciprocity_gate
- CONCESSION: Incremental give-and-take offers.
  Subtypes: staged_concession, tradeoff_offer
- BUNDLING: Packaging or adding items/fees.
  Subtypes: add_on_bundle, take_it_or_leave_it_package
- PAYMENT_DEFLECTION: Steering to monthly payment instead of total price.
  Subtypes: monthly_focus, affordability_frame
- LOSS_AVERSION: Emphasizing loss if no action is taken.
  Subtypes: fear_of_missing_out, loss_warning
- SOCIAL_PROOF: Referencing others' choices to persuade.
  Subtypes: popularity_claim, herd_reference
- NONE: No tactic detected.
  Subtype: none

Competitor Mentions:
- If the NEW line references a competitor or "other dealer/offer", classify as ANCHORING (comparison_anchor), not SOCIAL_PROOF.

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
      "category": "ANCHORING | URGENCY | AUTHORITY | FRAMING | COMMITMENT_TRAP | CONCESSION | BUNDLING | PAYMENT_DEFLECTION | LOSS_AVERSION | SOCIAL_PROOF | NONE",
      "subtype": "string (from list above)",
      "confidence": float (0.0-1.0),
      "headline": "Short headline (e.g., 'Pricing Anchor Set')",
      "why": "One-sentence explanation of why it matters",
      "best_question": "Single best question to ask next",
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
                   headline=item.get("headline", item.get("message", "Signal detected")),
                   why=item.get("why", ""),
                   best_question=item.get("best_question", ""),
                   evidence=item.get("evidence", ""),
                   timestamp=target_segments[-1].timestamp, 
                   options=valid_options, 
                   message=item.get("message", "Signal Detected")
                )
                if signal.category == "FRAMING" and signal.confidence < 0.85:
                    continue
                if signal.category == "COMMITMENT_TRAP" and not _is_commitment_trap(signal.evidence):
                    signal.category = "NONE"
                    signal.subtype = "none"
                    signal.options = []
                # Re-map competitor mentions away from SOCIAL_PROOF
                if signal.category == "SOCIAL_PROOF" and _is_competitor_reference(signal.evidence):
                    signal.category = "ANCHORING"
                    signal.subtype = "comparison_anchor"
                if signal.category == "SOCIAL_PROOF" and _is_shopping_advice(signal.evidence):
                    signal.category = "NONE"
                    signal.subtype = "none"
                    signal.options = []
                if signal.category == "AUTHORITY" and signal.subtype == "policy_shield" and not signal.options:
                    signal.options = [
                        "Consider asking which parts of the policy are flexible versus fixed.",
                        "One option is to request a review or exception path.",
                        "Another approach could be to ask who can approve exceptions."
                    ]
                if signal.category == "SOCIAL_PROOF" and not signal.options:
                    signal.options = [
                        "Consider asking for evidence supporting the popularity claim.",
                        "One option is to request comparative data against other models.",
                        "Another approach could be to refocus on your specific requirements."
                    ]
                signals.append(signal)
            except Exception as e:
                logger.warning(f"V2 Skipping invalid signal item: {item} | Error: {e}")

        # Deterministic override for numeric anchors in NEW text (only if LLM returns NONE/empty)
        newest_text = target_segments[-1].text if target_segments else ""
        if _is_bundling_candidate(newest_text):
            if not signals or signals[0].category == "NONE":
                return [TacticSignal(
                    category="BUNDLING",
                    subtype="add_on_bundle",
                    confidence=1.0,
                    headline="Add-On Bundle Detected",
                    why="Bundled add-ons can inflate the total cost beyond the base offer.",
                    best_question="Which items are optional versus required in that bundle?",
                    evidence=newest_text,
                    timestamp=target_segments[-1].timestamp if target_segments else 0.0,
                    options=[
                        "Consider asking for a line-item breakdown of each add-on.",
                        "One option is to request the base price without bundled items.",
                        "Another approach could be to ask which items are required versus optional."
                    ],
                    message="Counterparty bundled add-ons into the offer."
                )]
        if _is_price_anchor_candidate(newest_text):
            if not signals or signals[0].category == "NONE":
                return [TacticSignal(
                    category="ANCHORING",
                    subtype="numeric_anchor",
                    confidence=1.0,
                    headline="Pricing Anchor Set",
                    why="First numbers tend to pull the negotiation toward them.",
                    best_question="What assumptions are baked into that number?",
                    evidence=newest_text,
                    timestamp=target_segments[-1].timestamp if target_segments else 0.0,
                    options=[
                        "Consider asking for a breakdown of how that figure was calculated.",
                        "One option is to pause and request external benchmarks before responding.",
                        "Another approach could be to introduce an alternative reference point."
                    ],
                    message="Counterparty stated a concrete price point."
                )]

        return signals

    async def generate_summary(self, transcript_text: str, outcome: dict, user_speaker_id: int = 0, negotiation_type: str = "General") -> ImprovementSummary:
        """
        Generate a strategic debrief of the negotiation.
        """
        user_role = f"Speaker {user_speaker_id}"
        
        # 1. Normalize Transcript Labels for AI Clarity
        # Convert "Speaker 0" or "unknown" to "[USER]" and others to "[OPPONENT]"
        # This prevents the LLM from hallucinating roles when diarization is imperfect.
        
        normalized_transcript = ""
        lines = transcript_text.split('\n')
        for line in lines:
            if ":" in line:
                speaker_part, text_part = line.split(":", 1)
                speaker_part = speaker_part.lower().strip()
                
                # Logic: If user is 0, then "0" or "unknown" is USER.
                # If user is 1, then "1" is USER.
                is_user = False
                if str(user_speaker_id) in speaker_part:
                    is_user = True
                elif user_speaker_id == 0 and "unknown" in speaker_part:
                    is_user = True
                
                label = "[USER]" if is_user else "[OPPONENT]"
                normalized_transcript += f"{label}: {text_part.strip()}\n"
            else:
                normalized_transcript += line + "\n"
        
        # 2. Aggregate Signals from Transcript Lines (like Practice Mode)
        # Build TranscriptSegment objects for each line and detect tactics on opponent lines.
        aggregated_signals_text = ""
        try:
            normalized_lines = normalized_transcript.strip().split('\n')
            for idx, line in enumerate(normalized_lines):
                if ": " in line and line.startswith("[OPPONENT]"):
                    text = line.split(": ", 1)[1]
                    # Create a minimal segment for detection
                    seg = TranscriptSegment(speaker="COUNTERPARTY", text=text)
                    # Call detect_tactics with this single line as "new"
                    signals = await self.detect_tactics(segments=[], new_segments=[seg], negotiation_type=negotiation_type)
                    for sig in signals:
                        if sig.category != "NONE":
                            # Format: "[LINE X] TACTIC: quote snippet"
                            snippet = text[:60] + "..." if len(text) > 60 else text
                            aggregated_signals_text += f"  - [LINE {idx+1}] {sig.category} ({sig.subtype}): \"{snippet}\"\n"
        except Exception as e:
            logger.warning(f"Signal aggregation failed: {e}")
            aggregated_signals_text = "  (Aggregation skipped due to error)\n"

        # 3. Build Pre-Identified Signals section for the prompt
        pre_signals_section = ""
        if aggregated_signals_text.strip():
            pre_signals_section = f"""
PRE-IDENTIFIED SIGNALS (from automated detection):
{aggregated_signals_text}
Use these pre-identified signals to guide your analysis. Include ALL of them in your tactics_faced list.
"""

        prompt = f"""
You are the world's best negotiation coach. Your client is [USER]. The opponent is [OPPONENT].
Context: {negotiation_type} negotiation.
Analyze this transcript from the [USER]'s perspective. Do NOT just critique the [OPPONENT]'s moves—critique how the [USER] *responded* to them.
{pre_signals_section}
Transcript:
{normalized_transcript[:10000]}

Outcome: {outcome.get('result', 'unknown')}

Task:
1. Identify specific tactics used AGAINST the [USER] (incorporate PRE-IDENTIFIED SIGNALS above).
2. Evaluate the [USER]'s counter-moves.
3. Score the [USER]'s performance (0-100).
4. Extract key moments where the [USER] won or lost ground.

MANDATORY JSON OUTPUT FORMAT (Strict):
{{
  "negotiation_summary": "High-level executive summary of the entire session (2-3 sentences)",
  "strong_move": "Best move by the User (e.g., 'You effectively anchored the price...')",
  "missed_opportunity": "Critical miss by the User (e.g., 'You failed to challenge the deadline...')",
  "improvement_tip": "One actionable tip for next time (e.g., 'Next time, use a Label when...')",
  "negotiation_score": integer (0-100),
  "tactics_faced": ["TACTIC: Specific Detail", "TACTIC: Specific Detail"], 
  "key_moments": [
    {{ "quote": "quote from transcript", "insight": "Why this mattered for the User..." }}
  ]
}}
IMPORTANT: 
- 'tactics_faced' strings MUST follow the format "TACTIC NAME: Brief Context" (e.g., "ANCHORING: Seller asked for $125k").
- Do NOT include 'expanded_insights'. 
- Speak directly to the User ("You did X").
"""

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
                     {"role": "system", "content": "You are a negotiation coach for the User. Return strictly valid JSON."},
                     {"role": "user", "content": prompt}
                 ],
                 max_tokens=1000,
                 temperature=0.6,
                 response_format={"type": "json_object"}
            )
            raw = response.choices[0].message.content
            data = attempt_parse(raw)
            if data is None:
                 # Retry once with stricter system prompt if JSON fails
                response = await self.client.chat.completions.create(
                     model="gpt-4o-mini",
                     messages=[
                         {"role": "system", "content": "Return valid JSON only. meaningful negotiation_score and key_moments are REQUIRED."},
                         {"role": "user", "content": prompt}
                     ],
                     max_tokens=1000,
                     temperature=0.0,
                     response_format={"type": "json_object"}
                 )
                raw = response.choices[0].message.content
                data = attempt_parse(raw)

            if data is None:
                raise ValueError("Invalid JSON from summary model")
            
            # Robust extraction
            score = 50
            raw_score = data.get("negotiation_score")
            if isinstance(raw_score, int):
                score = raw_score
            elif isinstance(raw_score, str) and raw_score.isdigit():
                score = int(raw_score)

            # Robust moments extraction
            raw_moments = data.get("key_moments", [])
            valid_moments = []
            if isinstance(raw_moments, list):
                for m in raw_moments:
                    if isinstance(m, dict) and "quote" in m and "insight" in m:
                        valid_moments.append(m)
            
            return ImprovementSummary(
                strong_move=str(data.get("strong_move", "N/A")),
                missed_opportunity=str(data.get("missed_opportunity", "N/A")),
                improvement_tip=str(data.get("improvement_tip", "N/A")),
                negotiation_score=score,
                negotiation_summary=str(data.get("negotiation_summary", "")),
                tactics_faced=[str(t) for t in data.get("tactics_faced", []) if isinstance(t, str)],
                key_moments=valid_moments
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

_AD_HINTS = [
    r"\bsponsored\b",
    r"\bthis episode is brought to you\b",
    r"\bpromo code\b",
    r"\buse code\b",
    r"\bsubscribe\b",
    r"\bad\b",
    r"\bcommercial\b",
    r"\bskip this one\b",
    r"\bvisit\b",
]


def _is_price_anchor_candidate(text: str) -> bool:
    lowered = text.lower()
    if any(hint in lowered for hint in _NON_NEGOTIATION_HINTS):
        return False
    return any(p.search(text) for p in _AMOUNT_PATTERNS)


def _is_ad_segment(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(hint, lowered) for hint in _AD_HINTS)


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
