from openai import AsyncOpenAI
import os
import logging
from .personalities import get_system_prompt, DEFAULT_PERSONALITY

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Coach:
    def __init__(self, personality: str = DEFAULT_PERSONALITY):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.personality = personality
        self.system_prompt = get_system_prompt(personality)
        logger.info(f"Coach initialized with personality: {personality}")

    def set_personality(self, personality: str):
        """Change the coaching personality."""
        self.personality = personality
        self.system_prompt = get_system_prompt(personality)
        logger.info(f"Coach personality changed to: {personality}")

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
                    - [COUNTERPARTY] makes an offer, demand, or statement that needs a response strategy
                    - [USER] is about to make a mistake (accepting too fast, revealing info, etc.)
                    - There's a tactical opportunity (silence, counter-offer, anchoring, etc.)
                    - [USER] sounds uncertain or needs encouragement
                    
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
        Generates short, tactical advice if warranted.
        Enforces the 15-word limit.
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Transcript: {transcript}\nAdvise:"}
                ],
                max_tokens=20,
                temperature=0.7
            )
            advice = response.choices[0].message.content.strip()
            
            # Post-processing enforcement
            word_count = len(advice.split())
            if word_count > 15:
                logger.warning(f"Advice blocked (Too long: {word_count} words): {advice}")
                return ""
                
            return advice
        except Exception as e:
            logger.error(f"Error generating advice: {e}")
            return ""
