# Semantic Voice Activity Detection (VAD)

## Overview
Traditional **VAD** relies soley on audio cues like energy levels and spectral tilt to detect speech. This leads to early cut-offs when the user pauses to think, or excessive delays when the user finishes speaking. 

**Semantic VAD** adds a GPT-2-based prediction model to understand whether the user has actually finished what they are saying. The model iteratively predicts the sum probability of the next token bein an end-of-sentence (EOS) marker (e.g., ".", "?", "!").

### Installation
```sh
# Clone the repository
git clone https://github.com/your-repo/victorfiz-speech.git
cd victorfiz-speech

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies 
npm install

# Add API keys to config.py
```
**Generate API keys** from [ElevenLabs](https://elevenlabs.io/app/settings/api-keys) and [Deepgram](https://developers.deepgram.com/docs/create-additional-api-keys)

### Running the Application
1. **Start the Flask backend**:
   ```sh
   python app.py
   ```
2. **Open `index.html` in a browser** to interact with the system.
3. **Activate the microphone** using the Start button.

## Project Structure
```plaintext
victorfiz-speech/
├── app.py          # Main backend Flask app handling real-time communication
├── config.py       # API keys and configurations
├── eos_prob.py     # Predicts the probability of an End-of-Sentence token
├── index.html      # Frontend UI for voice interaction
├── load_tokeniser.py  # Loads GPT-2 tokenizer and model for EOS probability
├── requirements.txt   # Dependencies
├── script.js      # Client-side handling of VAD and microphone input
├── speech_gen.py  # Handles text-to-speech generation
├── vad.py         # Implements VAD logic, real-time speech detection
└── model_data/    # Stores preloaded model files
```

## Key Functionalities
### `app.py`
- Runs a Flask server with WebSocket (SocketIO) support.
- Handles incoming transcripts and generates responses asynchronously.

### `vad.py`
- Uses Silero VAD (Torch) to detect speech activity.
- Implements **semantic EOS probability-based waiting time** to determine when to stop listening.
- Emits `vad_decision` and `speaking_status` events for real-time interaction.

### `eos_prob.py`
- Loads GPT-2 to compute EOS probabilities.
- Maps EOS probability to a **dynamic waiting time** (instead of a fixed silence threshold).

### `speech_gen.py`
- Streams text-to-speech responses using Eleven Labs API.
- Handles real-time speech synthesis with efficient chunking.

### `script.js`
- Captures microphone input.
- Sends speech data to the backend and receives VAD decisions.
- Controls start/stop speech detection based on AI turn-taking logic.

## Challenges
⚠ Requires **fast ASR transcription** for best results.
⚠ EOS probability needs fine-tuning.
⚠ Computational overhead is slightly higher than acoustic VAD.

---

