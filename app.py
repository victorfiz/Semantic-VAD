from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import websockets
import json
import base64
import logging
from openai import AsyncOpenAI
import time
import requests

logging.basicConfig(level=logging.INFO)

ELEVENLABS_API_KEY = 'd46e93087e0a30d3c77a28ba6bad8c8b'
VOICE_ID = '21m00Tcm4TlvDq8ikWAM'

app = Flask(__name__)
CORS(app)

chat_history = ["Instructions: Below is your conversation history. I want you to just output a short response to the user. Make your output extremely concise! Use umms and errs to sound human. I only want your response."]

async def chat_completion(query):
    url = "http://localhost:11434/api/generate"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "model": "phi3",
        "prompt": query
    }
    logging.info(f"----> Query sent to Ollama: {query}")
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers, stream=True)
        logging.info(f"Ollama status code: {response.status_code}")
        if response.status_code == 200:
            accumulated_response = ""
            try:
                for line in response.iter_lines():
                    if line:
                        res = line.decode('utf-8')
                        response_json = json.loads(res)
                        accumulated_response += response_json.get("response", "")
                        
                logging.info(f"----> Ollama returned: {accumulated_response}")
                return accumulated_response
            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode JSON: {e}")
        else:
            logging.error(f"Failed to get response. Status code: {response.status_code}")
            return ""
    except Exception as e:
        logging.error(f"Error connecting to local model: {e}")
        return ""

async def text_to_speech(voice_id, text):
    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id=eleven_monolingual_v1"
    try:
        async with websockets.connect(uri, ping_interval=10, ping_timeout=5) as websocket:
            await websocket.send(json.dumps({
                "text": text,
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
def return_speech():
    global chat_history
    data = request.get_json()
    transcript = data.get('transcript')
    if not transcript:
        return jsonify({'message': 'No transcript provided'}), 400
    
    chat_history.append(f"(user): {transcript}")
    spaced_chat_history = "\n\n".join(chat_history)

    try:
        text_response = asyncio.run(chat_completion(spaced_chat_history))
        
        audio_data = asyncio.run(text_to_speech(VOICE_ID, text_response))
        logging.info("text_response received")
        chat_history.append(f"(your response): {text_response}")
        
        if audio_data:
            return jsonify({
                'message': 'Transcript processed and response generated successfully',
                'response': text_response,
                'audio': base64.b64encode(audio_data).decode('utf-8')
            }), 200
        else:
            return jsonify({'message': 'Transcript processed, but no audio generated', 'response': text_response}), 500
    except Exception as e:
        logging.error(f"Error processing transcript: {e}")
        return jsonify({'message': str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5001)
