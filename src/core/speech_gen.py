import asyncio
import aiohttp
import json
import websockets
from config.config import ELEVENLABS_API_KEY, VOICE_ID

async def text_chunker(chunks):
    splitters = (".", "?", "!", " ")
    buffer = ""

    async for chunk in chunks:
        if buffer.endswith(splitters):
            yield buffer + " "
            buffer = chunk
        elif chunk.startswith(splitters):
            yield buffer + chunk[0] + " "
            buffer = chunk[1:]
        else:
            buffer += chunk

    if buffer:
        yield buffer + " "

async def text_to_speech_input_streaming(socketio, VOICE_ID, text_iterator):
    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream-input?model_id=eleven_turbo_v2"

    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({
            "text": " ",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
            "xi_api_key": ELEVENLABS_API_KEY,
        }))

        async def listen():
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    if data.get("audio"):
                        socketio.emit('audio', {'audio': data["audio"]})
                    elif data.get('isFinal'):
                        break
                except websockets.exceptions.ConnectionClosed:
                    break

        listen_task = asyncio.create_task(listen())

        async for text in text_chunker(text_iterator):
            await websocket.send(json.dumps({"text": text, "try_trigger_generation": True}))

        await websocket.send(json.dumps({"text": ""}))

        await listen_task

async def async_chat_completion(socketio, query):
    url = "http://localhost:11434/api/generate"
    headers = {"Content-Type": "application/json"}
    payload = {"model": "mistral:instruct", "prompt": query}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:

            async def text_iterator():
                async for line in response.content:
                    data = json.loads(line.decode('utf-8'))
                    text_chunk = data.get('response', '')
                    if text_chunk.strip():
                        socketio.emit('response', {'text': text_chunk})
                        yield text_chunk

            await text_to_speech_input_streaming(socketio, VOICE_ID, text_iterator())

            socketio.emit('response', {'done': True})

def run_async_chat_completion(socketio, query):
    asyncio.run(async_chat_completion(socketio, query))
