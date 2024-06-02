from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO

from speech_gen import run_async_chat_completion
from vad import print_audio
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/script.js')
def script():
    return send_file('script.js')

# Takes in response from /send_text, emits voice audio chat completion, and updates chat_history
chat_history = ["Instructions: Below is your conversation history. I want you to just output a short response to the user. Make your output extremely concise! Use umms and errs to sound human. I only want your response."]

@app.route('/send_text', methods=['POST'])
def send_text():
    global chat_history

    data = request.get_json()
    transcript = data['text']
    response = data.get('response', '')  

    chat_history[-1] += response

    chat_history.append(f"(user): {transcript}")
    chat_history.append("(your response): ")
    query = "\n\n".join(chat_history)

    socketio.start_background_task(run_async_chat_completion, socketio, query)
    return jsonify({"status": "Processing"}), 202

# Takes in audio from captureMicrophoneAudio(), emits vad_decision()'s vad_output
@socketio.on('vad_audio')
def handle_audio_data(audio_data):
    socketio.start_background_task(print_audio, socketio, audio_data)
    return jsonify({"status": "Audio returning"}), 202

if __name__ == '__main__':
    socketio.run(app, port=5001)