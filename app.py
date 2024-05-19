from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import websockets
import json
import base64
import logging
from openai import AsyncOpenAI
import time

# Configure logging
logging.basicConfig(level=logging.INFO)

# Define API keys
OPENAI_API_KEY = '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'
ELEVENLABS_API_KEY = 'd46e93087e0a30d3c77a28ba6bad8c8b'
VOICE_ID = '21m00Tcm4TlvDq8ikWAM'

# Set OpenAI API key
aclient = AsyncOpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

async def chat_completion(query):
    try:
        response = await aclient.chat.completions.create(
            model='gpt-4-turbo',
            messages=[{'role': 'user', 'content': query}],
            temperature=1
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error during OpenAI API call: {e}")
        raise e

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
                    data = json.loads(message)
                    if "audio" in data:
                        audio_data += base64.b64decode(data["audio"])
                    elif data.get('isFinal'):
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

@app.route('/send_transcript', methods=['POST'])
def handle_transcript():
    data = request.get_json()
    transcript = data.get('transcript')
    if not transcript:
        return jsonify({'message': 'No transcript provided'}), 400

    try:
        full_response = asyncio.run(chat_completion(transcript))
        audio_data = asyncio.run(text_to_speech(VOICE_ID, full_response))

        if audio_data:
            return jsonify({
                'message': 'Transcript processed and response generated successfully',
                'response': full_response,
                'audio': base64.b64encode(audio_data).decode('utf-8')
            }), 200
        else:
            return jsonify({'message': 'Transcript processed, but no audio generated', 'response': full_response}), 500
    except Exception as e:
        logging.error(f"Error processing transcript: {e}")
        return jsonify({'message': str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5001)
