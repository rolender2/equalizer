import os
import asyncio
import logging
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv

from services.audio_processor import AudioProcessor
from services.coach import Coach
from services.personalities import list_personalities, DEFAULT_PERSONALITY, list_negotiation_types, DEFAULT_NEGOTIATION_TYPE
from services.session_recorder import SessionRecorder

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


@app.get("/personalities")
async def get_personalities():
    """List available coach personalities."""
    return JSONResponse(content={
        "personalities": list_personalities(),
        "default": DEFAULT_PERSONALITY
    })

@app.get("/negotiation-types")
async def get_negotiation_types():
    """List available negotiation types."""
    return JSONResponse(content={
        "types": list_negotiation_types(),
        "default": DEFAULT_NEGOTIATION_TYPE
    })


from pydantic import BaseModel

class OutcomeRequest(BaseModel):
    result: str
    confidence: int
    notes: str = ""

@app.post("/sessions/{session_id}/outcome")
async def save_session_outcome(session_id: str, outcome: OutcomeRequest):
    """Save the outcome for a completed session."""
    logger.info(f"Received outcome for session {session_id}: {outcome}")
    success = SessionRecorder.update_outcome(
        session_id, 
        outcome.result, 
        outcome.confidence, 
        outcome.notes
    )
    if success:
        return {"status": "success"}
    return JSONResponse(status_code=404, content={"message": "Session not found"})


@app.post("/sessions/{session_id}/summary")
async def generate_session_summary(session_id: str, expanded: bool = False):
    """Generate a post-session reflection summary."""
    from pathlib import Path
    import json as json_module
    
    project_root = Path(__file__).resolve().parent.parent
    session_path = project_root / "sessions" / f"{session_id}.json"
    
    if not session_path.exists():
        return JSONResponse(status_code=404, content={"message": "Session not found"})
    
    try:
        with open(session_path, 'r') as f:
            session_data = json_module.load(f)
        
        # Build transcript text
        transcripts = session_data.get("transcripts", [])
        transcript_text = "\n".join([
            f"[{t.get('speaker', 'UNKNOWN')}]: {t.get('text', '')}" 
            for t in transcripts
        ])
        
        outcome = session_data.get("outcome") or {}
        negotiation_type = session_data.get("negotiation_type", "General")
        
        # Create a Coach instance for summary generation
        # Mode doesn't strictly matter here as we call generate_summary directly
        coach = Coach(negotiation_type=negotiation_type, mode="debrief")
        summary = await coach.generate_summary(transcript_text, outcome, expanded=expanded)
        
        # Save summary to session file
        session_data["reflection"] = summary
        session_data["summary_details"] = {
            "total_transcripts": len(transcripts),
            "total_advice": len(session_data.get("advice_given", [])),
            "expanded": bool(expanded),
            "generated_at": __import__("datetime").datetime.now().isoformat()
        }
        with open(session_path, 'w') as f:
            json_module.dump(session_data, f, indent=2)
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        # Persist failure for debugging
        try:
            session_data["reflection_error"] = str(e)
            with open(session_path, 'w') as f:
                json_module.dump(session_data, f, indent=2)
        except Exception:
            pass
        return JSONResponse(status_code=500, content={"message": str(e)})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected")
    
    # Defaults
    coach = Coach(mode="debrief", negotiation_type=DEFAULT_NEGOTIATION_TYPE)
    recorder = SessionRecorder(personality="tactical", negotiation_type=DEFAULT_NEGOTIATION_TYPE)
    
    # Send session ID to frontend immediately
    await websocket.send_text(json.dumps({
        "type": "session_init",
        "session_id": recorder.session_id
    }))
    
    # Callback to run when Deepgram detects a sentence/pause
    def on_transcript(transcript: str, speaker: int = 0):
        # Pass raw speaker ID to recorder and coach
        # They will handle mapping based on configuration
        
        # Record the transcript with speaker
        recorder.add_transcript(transcript, speaker=speaker)
        
        # Schedule async coach processing
        # We process every transcript; the coach internally handles buffering and debrief logic.
        asyncio.run_coroutine_threadsafe(
            process_transcript_and_advise(transcript, speaker, websocket, coach, recorder), 
            loop
        )

    # Initialize AudioProcessor with the callback
    processor = AudioProcessor(transcript_callback=on_transcript)
    await processor.start()
    
    # Capture the main event loop
    loop = asyncio.get_running_loop()

    try:
        while True:
            # Receive data from Frontend
            message = await websocket.receive()
            
            # Check for disconnect message
            if message.get("type") == "websocket.disconnect":
                logger.info("Client disconnected gracefully")
                break
            
            if "bytes" in message:
                # Binary audio chunk from microphone (or mixed audio)
                await processor.send_audio(message["bytes"])
            elif "text" in message:
                # Text message - personality change or other commands
                try:
                    data = json.loads(message["text"])
                    
                    if data.get("type") == "config":
                        # Updated Init / Pre-flight config
                        new_type = data.get("negotiation_type", DEFAULT_NEGOTIATION_TYPE)
                        mode = data.get("mode", "debrief") # Default to debrief if missing
                        user_id = data.get("user_speaker_id", 0)
                        emit_interim = data.get("emit_interim", False)
                        endpointing_ms = data.get("endpointing_ms")
                        window_override = data.get("window_size_seconds")
                        test_mode = data.get("test_mode_counterparty", False)
                        
                        coach.set_negotiation_type(new_type)
                        coach.set_mode(mode)
                        coach.set_user_speaker_id(user_id)
                        processor.set_emit_interim(emit_interim)
                        if endpointing_ms is not None:
                            processor.set_endpointing(endpointing_ms)
                        if window_override is not None:
                            coach.window_size_seconds = float(window_override)
                        coach.set_test_mode_counterparty(test_mode)
                        
                        # Update recorder context
                        recorder.negotiation_type = new_type
                        # (SessionRecorder doesn't strictly track 'mode' yet, but we could add it if needed)
                        
                        # Handle personality if sent
                        if "personality" in data:
                            # Note: New coach refactor removed personality from constructor/methods 
                            # as it delegates to Core Engine which is persona-agnostic (pure tactic detection).
                            # We keep it in recorder for metadata if desired.
                            recorder.set_personality(data["personality"])
                        
                        logger.info(f"Session configured: Type={new_type} | Mode={mode}")
                    
                    elif data.get("type") == "personality":
                        # Legacy support or if we want to store personality in metadata
                        p = data.get("personality", DEFAULT_PERSONALITY)
                        recorder.set_personality(p)
                        # We don't update coach personality anymore since core is neutral
                        await websocket.send_text(json.dumps({
                            "type": "personality_changed",
                            "personality": p
                        }))
                        
                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON: {message['text']}")
            
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Connection error: {e}")
    finally:
        await processor.stop()
        recorder.close()


async def process_transcript_and_advise(
    transcript: str,
    speaker: int | str,
    websocket: WebSocket, 
    coach: Coach,
    recorder: SessionRecorder
):
    """
    Ingest transcript into Coach.
    If advice is returned (Live Mode only), send to UI.
    """
    logger.info(f"Processing [{speaker}]: {transcript}")
    
    # Coach handles buffering and mode logic internally.
    # Returns advice string only if live mode triggers a signal.
    advice = await coach.process_transcript(transcript, speaker)
    
    if advice:
        logger.info(f"Sending Live Advice: {advice}")
        recorder.add_advice(advice)
        await websocket.send_text(json.dumps({
            "type": "advice",
            "content": advice
        }))

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
