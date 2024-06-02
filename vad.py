import numpy as np
from collections import deque
import torch
import torchaudio
torch.set_num_threads(1)

data_transmission_started = False

audio_buffer = deque(maxlen=44100 * 5)  
vad_buffer = deque(maxlen=44100 * 5)

model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=True)
(get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils

def validate(model, inputs: torch.Tensor, sr: int):
    with torch.no_grad():
        outs = model(inputs, sr)
    return outs

def resample(audio, orig_sr, target_sr):
    resample_transform = torchaudio.transforms.Resample(orig_freq=orig_sr, new_freq=target_sr)
    return resample_transform(audio)

# main function
def print_audio(socketio, audio_data):
    global audio_buffer, vad_buffer, data_transmission_started

    audio_samples = np.frombuffer(audio_data, dtype=np.float32)
    audio_buffer.extend(audio_samples)

    vad_output = None  # Initialize vad_output

    if len(audio_buffer) % 44100 == 0:
        audio_samples_writable = np.copy(audio_samples)
        audio_samples_tensor = torch.from_numpy(audio_samples_writable).unsqueeze(0)
        audio_samples_resampled = resample(audio_samples_tensor, orig_sr=44100, target_sr=16000)
        
        vad_output = validate(model, audio_samples_resampled, sr=16000)[0].item()

    # Ensure vad_output has a value before emitting
    if vad_output is not None:
        if not data_transmission_started:  # Check if transmission has not started
            print("Data transmission begins for audio_vad")  # Log message
            data_transmission_started = True  # Set the flag to True
        socketio.emit('audio_vad', {'audio': vad_output})





