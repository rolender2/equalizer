import os
import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

from services.audio_processor import AudioProcessor
from services.coach import Coach

# Load env variables
load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Coach (Global for MVP simplicty, ideally per-session)
coach = Coach()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected")
    
    # Callback to run when Deepgram detects a sentence/pause
    def on_transcript(transcript: str):
        # We need to schedule the async coach processing from this sync callback
        asyncio.run_coroutine_threadsafe(process_transcript_and_advise(transcript, websocket), loop)

    # Initialize AudioProcessor with the callback
    processor = AudioProcessor(transcript_callback=on_transcript)
    await processor.start()
    
    # Capture the main event loop
    loop = asyncio.get_running_loop()

    try:
        while True:
            # Receive binary audio chunks from Frontend (Microphone)
            data = await websocket.receive_bytes()
            # Stream to Deepgram
            await processor.send_audio(data)
            
    except WebSocketDisconnect:
        logger.info("Client disconnected")
        await processor.stop()
    except Exception as e:
        logger.error(f"Connection error: {e}")
        await processor.stop()

async def process_transcript_and_advise(transcript: str, websocket: WebSocket):
    """
    The Brain Logic:
    1. Check if advice is necessary.
    2. If yes, generate advice.
    3. Send to Frontend.
    """
    logger.info(f"Processing transcript: {transcript}")
    
    # Step 1: Gatekeeper
    if await coach.evaluate_necessity(transcript):
        logger.info("Advice WARRANTED. Generating...")
        
        # Step 2: Generation
        advice = await coach.generate_advice(transcript)
        
        if advice:
            logger.info(f"Sending Advice: {advice}")
            # Step 3: Send to UI
            await websocket.send_text(advice)
    else:
        logger.info("Advice NOT warranted.")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
