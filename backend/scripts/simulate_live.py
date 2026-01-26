import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
from services.coach import Coach

# Load env
load_dotenv()

# To fix imports path
sys.path.append(os.getcwd())

async def run_sim():
    # Logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("Simulation")
    
    logger.info("Starting Live Simulation...")
    
    # Init Coach (Live Mode)
    coach = Coach(mode="live", negotiation_type="General", user_speaker_id=0)
    coach.window_size_seconds = 0.0 # Force processing every time
    
    # 1. User says something (Speaker 0)
    print("\n--- Step 1: User speaks ---")
    res = await coach.process_transcript("I am not sure about this.", "Speaker 0")
    if res: print(f"Output: {res}")
    else: print("Output: None (Silent)")
    
    # 2. Counterparty says something benign (Speaker 1)
    print("\n--- Step 2: Counterparty speaks (Benign) ---")
    res = await coach.process_transcript("We can discuss the details.", "Speaker 1")
    if res: print(f"Output: {res}")
    else: print("Output: None (Silent)")

    # 3. Counterparty uses Urgency (Speaker 1)
    print("\n--- Step 3: Counterparty speaks (Urgency) ---")
    # This assumes LLM is reachable and working. If not, this might fail or return None if detection fails.
    # Assuming valid API key is in environment.
    res = await coach.process_transcript("This offer is only valid today.", "Speaker 1")
    if res: print(f"Output: {res}")
    else: print("Output: None (Silent)")
    
    # 4. Same Urgency immediately (Dedupe check)
    print("\n--- Step 4: Counterparty repeats Urgency (Dedupe) ---")
    res = await coach.process_transcript("Really, only today.", "Speaker 1")
    if res: print(f"Output: {res}")
    else: print("Output: None (Silent - Deduped)")

if __name__ == "__main__":
    asyncio.run(run_sim())
