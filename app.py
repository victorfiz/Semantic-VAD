from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import websockets
import json
import base64
import logging
from openai import AsyncOpenAI

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Define API keys
OPENAI_API_KEY = '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'
ELEVENLABS_API_KEY = 'd46e93087e0a30d3c77a28ba6bad8c8b'
VOICE_ID = '21m00Tcm4TlvDq8ikWAM'

# Set OpenAI API key
aclient = AsyncOpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

async def chat_completion(query):
    """Retrieve text from OpenAI and log the response."""
    logging.debug(f"Received query: {query}")
    try:
        response = await aclient.chat.completions.create(
            model='gpt-4',
            messages=[{'role': 'user', 'content': query}],
            temperature=1,
            stream=False  # Disable streaming for simplified logging
        )
        logging.debug("OpenAI API call succeeded")

        # Log the complete response received from OpenAI
        logging.debug(f"Received OpenAI response: {response}")

        # Correctly extract and return the response text
        response_text = response.choices[0].message.content
        logging.debug(f"Extracted response text: {response_text}")
        return response_text

    except Exception as e:
        logging.error(f"Error during OpenAI API call: {e}")
        raise e

async def text_to_speech(voice_id, text):
    """Send text to ElevenLabs API and return the audio data."""
    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id=eleven_monolingual_v1"
    logging.debug(f"Connecting to ElevenLabs API at {uri}")

    try:
        async with websockets.connect(uri, ping_interval=10, ping_timeout=5) as websocket:
            logging.debug("WebSocket connection opened")

            await websocket.send(json.dumps({
                "text": text,
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
                "xi_api_key": ELEVENLABS_API_KEY,
            }))
            logging.debug("Sent text to ElevenLabs API")

            # Send an empty string to signal the end of input
            await websocket.send(json.dumps({
                "text": "",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
                "xi_api_key": ELEVENLABS_API_KEY,
            }))
            logging.debug("Sent end-of-input signal to ElevenLabs API")

            audio_data = b""
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    logging.debug(f"Received message from ElevenLabs API: {data}")
                    if data.get("audio"):
                        logging.debug("Received audio data from ElevenLabs API")
                        audio_data += base64.b64decode(data["audio"])
                    elif data.get('isFinal'):
                        logging.debug("Final message received from ElevenLabs API")
                        break
                except websockets.exceptions.ConnectionClosed as e:
                    logging.error(f"WebSocket connection closed with error: {e}")
                    break
                except Exception as e:
                    logging.error(f"Error during WebSocket communication: {e}")
                    break

            logging.debug(f"Total audio data length: {len(audio_data)} bytes")
            logging.debug("Received complete audio data from ElevenLabs API")
            return audio_data
    except Exception as e:
        logging.error(f"Error connecting to ElevenLabs API: {e}")
        return b""

@app.route('/send_transcript', methods=['POST'])
def handle_transcript():
    logging.debug("Received request at /send_transcript")
    data = request.get_json()
    transcript = data.get('transcript')
    logging.debug(f"Transcript received: {transcript}")
    if not transcript:
        logging.error("No transcript provided")
        return jsonify({'message': 'No transcript provided'}), 400

    try:
        logging.debug("Starting chat_completion")
        full_response = asyncio.run(chat_completion(transcript))
        logging.debug(f"chat_completion executed successfully with response: {full_response}")

        logging.debug("Starting text_to_speech")
        audio_data = asyncio.run(text_to_speech(VOICE_ID, full_response))
        logging.debug("text_to_speech executed successfully")

        # Return the response and audio data as base64
        if audio_data:
            return jsonify({
                'message': 'Transcript processed and response generated successfully',
                'response': full_response,
                'audio': base64.b64encode(audio_data).decode('utf-8')
            }), 200
        else:
            logging.error("No audio data generated")
            return jsonify({'message': 'Transcript processed, but no audio generated', 'response': full_response}), 500
    except Exception as e:
        logging.error(f"Error processing transcript: {e}")
        return jsonify({'message': str(e)}), 500

if __name__ == "__main__":
    logging.debug("Starting Flask server...")
    app.run(debug=True, port=5001)
