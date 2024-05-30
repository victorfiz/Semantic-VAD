from flask import request, jsonify
import asyncio
import logging
from chat import chat_completion
from tts import text_to_speech
from config import VOICE_ID
import base64

chat_history = ["Instructions: Below is your conversation history. I want you to just output a short response to the user. Make your output extremely concise! Use umms and errs to sound human. I only want your response."]

def setup_routes(app):
    @app.route('/send_transcript', methods=['POST'])
    def return_speech():
        global chat_history
        data = request.get_json()
        transcript = data.get('transcript')
        if not transcript:
            return jsonify({'message': 'No transcript provided'}), 400
        
        chat_history.append(f"(user): {transcript}")
        chat_history.append("(your response): ")
        spaced_chat_history = "\n\n".join(chat_history)

        try:
            text_response = asyncio.run(chat_completion(spaced_chat_history))
            audio_data = asyncio.run(text_to_speech(VOICE_ID, text_response))
            chat_history[-1] += text_response
            
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