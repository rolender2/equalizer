import os
import logging
import json
import asyncio
import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)

DEEPGRAM_URL = "wss://api.deepgram.com/v1/listen"

class AudioProcessor:
    """
    Handles streaming audio to Deepgram using raw WebSockets.
    """
    def __init__(self, transcript_callback):
        self.transcript_callback = transcript_callback
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        self.ws = None
        self._receive_task = None
        self._connected = False

    async def start(self):
        """Initializes the Deepgram WebSocket Connection."""
        try:
            # Build the URL with query parameters
            url = (
                f"{DEEPGRAM_URL}"
                f"?model=nova-2"
                f"&language=en-US"
                f"&smart_format=true"
                f"&encoding=linear16"
                f"&channels=1"
                f"&sample_rate=16000"
                f"&endpointing=300"
            )

            # Connect with API key in header
            self.ws = await websockets.connect(
                url,
                additional_headers={"Authorization": f"Token {self.api_key}"}
            )
            self._connected = True
            
            logger.info("Deepgram WebSocket Connection Established")

            # Start receiving messages in the background
            self._receive_task = asyncio.create_task(self._receive_messages())
            return True

        except Exception as e:
            logger.error(f"Error starting AudioProcessor: {e}")
            self._connected = False
            return False

    async def _receive_messages(self):
        """Background task to receive and process transcripts from Deepgram."""
        try:
            async for message in self.ws:
                data = json.loads(message)
                
                # Check if this is a transcript result
                if data.get("type") == "Results":
                    channel = data.get("channel", {})
                    alternatives = channel.get("alternatives", [])
                    
                    if alternatives:
                        transcript = alternatives[0].get("transcript", "")
                        is_final = data.get("is_final", False)
                        speech_final = data.get("speech_final", False)
                        
                        if transcript and speech_final:
                            logger.info(f"Speech Final: {transcript}")
                            if self.transcript_callback:
                                self.transcript_callback(transcript)
                        elif transcript and is_final:
                            logger.debug(f"Intermediate Final: {transcript}")
                            
        except ConnectionClosed:
            logger.info("Deepgram connection closed")
            self._connected = False
        except Exception as e:
            logger.error(f"Error receiving from Deepgram: {e}")
            self._connected = False

    async def send_audio(self, audio_data: bytes):
        """Sends raw audio bytes to Deepgram."""
        if self.ws and self._connected:
            try:
                await self.ws.send(audio_data)
            except Exception as e:
                logger.error(f"Error sending audio: {e}")
                self._connected = False

    async def stop(self):
        """Closes the connection."""
        self._connected = False
        if self._receive_task:
            self._receive_task.cancel()
        if self.ws:
            await self.ws.close()
            logger.info("Deepgram Connection Closed")
