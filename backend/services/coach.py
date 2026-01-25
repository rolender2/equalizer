from openai import AsyncOpenAI
import os
import json
import logging
from .personalities import get_system_prompt, DEFAULT_PERSONALITY, DEFAULT_NEGOTIATION_TYPE

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Coach:
    def __init__(self, personality: str = DEFAULT_PERSONALITY, negotiation_type: str = DEFAULT_NEGOTIATION_TYPE):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.personality = personality
        self.negotiation_type = negotiation_type
        self.system_prompt = get_system_prompt(personality, negotiation_type)
        logger.info(f"Coach initialized: {personality} | {negotiation_type}")

    def set_personality(self, personality: str):
        """Change the coaching personality."""
        self.personality = personality
        self.system_prompt = get_system_prompt(personality, self.negotiation_type)
        logger.info(f"Coach personality changed to: {personality}")

    def set_negotiation_type(self, negotiation_type: str):
        """Change the evaluation context."""
        self.negotiation_type = negotiation_type
        self.system_prompt = get_system_prompt(self.personality, negotiation_type)
        logger.info(f"Coach negotiation type changed to: {negotiation_type}")

    async def evaluate_necessity(self, transcript: str) -> bool:
        """
        Determines if advice is warranted based on the transcript.
        Now speaker-aware: prioritizes advice when counterparty speaks.
        """
        if not transcript or len(transcript.strip()) < 10:
            return False

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": """You are a negotiation coach watching a live conversation.
                    Transcripts are labeled as [USER] (your client) or [COUNTERPARTY] (the other side).
                    
                    Say YES if:
                    - [COUNTERPARTY] makes an offer, demand, or RIGID statement ("non-negotiable", "policy")
                    - [COUNTERPARTY] pushes back or gives an ultimatum
                    - [USER] threatens to leave or mentions competitors (BATNA)
                    - [USER] is about to make a mistake (accepting too fast, revealing info)
                    - There's a tactical opportunity (silence, counter-offer, anchoring)
                    
                    Say NO if:
                    - It's completely irrelevant small talk
                    - [USER] is doing well and doesn't need intervention
                    
                    Reply ONLY 'YES' or 'NO'."""},
                    {"role": "user", "content": transcript}
                ],
                max_tokens=2,
                temperature=0
            )
            decision = response.choices[0].message.content.strip().upper()
            logger.info(f"Necessity check result: {decision}")
            return decision == "YES"
        except Exception as e:
            logger.error(f"Error evaluating necessity: {e}")
            return False

    async def generate_advice(self, transcript: str) -> str:
        """
        Generates advice using the JSON Signal architecture.
        Parses JSON, checks confidence, and returns formatted string for frontend.
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Transcript: {transcript}"}
                ],
                max_tokens=150, # Increased for JSON
                temperature=0.6,
                response_format={"type": "json_object"} # Enforce JSON
            )
            content = response.choices[0].message.content.strip()
            
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response: {content}")
                return ""

            # Check confidence gate
            confidence = data.get("confidence", 0)
            if confidence < 0.7:
                logger.info(f"Advice gated (Confidence {confidence} < 0.7)")
                return ""

            # Check if signal is 'none'
            if data.get("type") == "none":
                return ""

            # Format for frontend (Legacy Text Mode for now)
            # ⚠️ SIGNAL
            # • Option 1
            # • Option 2
            signal_msg = data.get("message", "Signal detected")
            options = data.get("options", [])
            
            formatted_advice = f"⚠️ {signal_msg.upper()}"
            for opt in options:
                formatted_advice += f"\n• {opt}"

            logger.info(f"Generated Signal: {formatted_advice}")
            return formatted_advice

        except Exception as e:
            logger.error(f"Error generating advice: {e}")
            return ""
