from openai import AsyncOpenAI
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Coach:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.system_prompt = """You are a Tactical Negotiation Commander. 
        Your goal is to provide real-time, imperative advice to a negotiator.
        
        RULES:
        1. Output MUST be an imperative command (e.g., "Stop talking.", "Ask for the price.").
        2. Output MUST be LESS THAN 15 WORDS.
        3. NO explanations. NO emojis. NO metadata.
        """

    async def evaluate_necessity(self, transcript: str) -> bool:
        """
        Determines if advice is warranted based on the transcript.
        For MVP: More permissive to demonstrate the UI.
        """
        if not transcript or len(transcript.strip()) < 10:
            return False

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": """You are a negotiation coach watching a live conversation. 
                    Your job is to decide if you should interrupt with tactical advice.
                    
                    Say YES if:
                    - The speaker is about to make a mistake (accepting too fast, revealing information, etc.)
                    - There's a tactical opportunity (silence, counter-offer, etc.)
                    - The speaker sounds uncertain or is asking for help
                    
                    Say NO only if the speech is completely irrelevant small talk.
                    
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
        Enforces the 7-word limit.
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
