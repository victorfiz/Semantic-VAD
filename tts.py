import json
import base64
import logging
import time
import websockets
from config import ELEVENLABS_API_KEY, VOICE_ID

async def text_to_speech(voice_id, text):
    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id=eleven_monolingual_v1"
    try:
        async with websockets.connect(uri, ping_interval=10, ping_timeout=5) as websocket:
            await websocket.send(json.dumps({
                "text": text,
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
                "xi_api_key": ELEVENLABS_API_KEY,
            }))
            await websocket.send(json.dumps({
                "text": "",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
                "xi_api_key": ELEVENLABS_API_KEY,
            }))

            audio_data = b""
            start_time = time.time()

            while True:
                try:
                    message = await websocket.recv()
                    if message:
                        data = json.loads(message)
                        if "audio" in data:
                            audio_data += base64.b64decode(data["audio"])
                        elif data.get('isFinal'):
                            break
                    else:
                        logging.warning("Received None message from WebSocket")
                        break
                except websockets.exceptions.ConnectionClosed as e:
                    logging.error(f"WebSocket connection closed with error: {e}")
                    break
                except Exception as e:
                    logging.error(f"Error during WebSocket communication: {e}")
                    break

            time_taken = time.time() - start_time
            logging.info(f"Time taken for text_to_speech: {time_taken:.2f} seconds")

            return audio_data
    except Exception as e:
        logging.error(f"Error connecting to ElevenLabs API: {e}")
        return b""