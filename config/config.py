import os
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY', '')
VOICE_ID = os.getenv('VOICE_ID', '')
HUGGINGFACE_TOKEN = os.getenv('HUGGINGFACE_TOKEN', '')
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY', '')
