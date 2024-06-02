from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO

from speech_gen import run_async_chat_completion
from vad import random_gen

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/script.js')
def script():
    return send_file('script.js')

chat_history = ["Instructions: Below is your conversation history. I want you to just output a short response to the user. Make your output extremely concise! Use umms and errs to sound human. I only want your response."]

@app.route('/send_text', methods=['POST'])
def send_text():
    global chat_history

    data = request.get_json()
    transcript = data['text']
    response = data['response']

    chat_history[-1] += response

    chat_history.append(f"(user): {transcript}")
    chat_history.append("(your response): ")
    query = "\n\n".join(chat_history)

    socketio.start_background_task(run_async_chat_completion, socketio, query)
    return jsonify({"status": "Processing"}), 202

@app.route('/send_num', methods=['POST'])
def send_num():
    socketio.start_background_task(random_gen, socketio)
    return jsonify({"status": "Processing"}), 202

if __name__ == '__main__':
    socketio.run(app, port=5001)