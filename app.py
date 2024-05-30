from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO

from speech_gen import run_async_chat_completion

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/send_text', methods=['POST'])
def send_text():
    data = request.get_json()
    query = data['text']
    socketio.start_background_task(run_async_chat_completion, socketio, query)
    return jsonify({"status": "Processing"}), 202

if __name__ == '__main__':
    socketio.run(app, port=5001)
