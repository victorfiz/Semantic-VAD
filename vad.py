import numpy as np
from collections import deque
import torch
import torchaudio
import time
from eos_prob import calculate_end_tokens_prob

torch.set_num_threads(1)

audio_buffer = deque(maxlen=44100 * 5)
vad_buffer = deque(maxlen=44100 * 5)
data_transmission_started = False
consecutive_below_threshold = 0
vad_threshold = 0.4
consecutive_threshold = 6
speaking = False
previous_transcript = ""
transcript_buffer = ""

# Load VAD model
model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=True)
(get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils

def validate(model, inputs: torch.Tensor, sr: int):
    with torch.no_grad():
        outs = model(inputs, sr)
    return outs

def resample(audio, orig_sr, target_sr):
    resample_transform = torchaudio.transforms.Resample(orig_freq=orig_sr, new_freq=target_sr)
    return resample_transform(audio)

def print_audio(socketio, audio_data=None, transcript=None):
    global audio_buffer, vad_buffer, data_transmission_started
    global consecutive_below_threshold, speaking, eos_prob
    global previous_transcript, transcript_buffer

    if transcript:
        socketio.emit('vad_decision', {'transcript': transcript})
    
    if transcript == None:
        transcript = transcript_buffer
    else:
        transcript_buffer = transcript
    
    if audio_data:
        audio_samples = np.frombuffer(audio_data, dtype=np.float32)
        audio_buffer.extend(audio_samples)

        vad_output = None

        if len(audio_buffer) % 44100 == 0:
            audio_samples_writable = np.copy(audio_samples)
            audio_samples_tensor = torch.from_numpy(audio_samples_writable).unsqueeze(0)
            audio_samples_resampled = resample(audio_samples_tensor, orig_sr=44100, target_sr=16000)
            # VAD [0,1] generated
            vad_output = validate(model, audio_samples_resampled, sr=16000)[0].item()

        if vad_output is not None:
            if not data_transmission_started:  
                print("VAD decisions emitting to client")  
                data_transmission_started = True  
            socketio.emit('vad_decision', {'vad_output': vad_output})
            
            print(f"vad:{vad_output:.3f}")

            if speaking:
                if vad_output < vad_threshold:
                    consecutive_below_threshold += 1
                else:
                    consecutive_below_threshold = 0

                if transcript != previous_transcript:
                    previous_transcript = transcript
                    print(f"new trans: {transcript}")
                    start_time = time.time()
                    eos_prob = calculate_end_tokens_prob(transcript) + 0.001
                    print(f"log_prob calculated:{eos_prob} for trans: {transcript}")

                    wait_time = ((1 /eos_prob)-1)/2

                    while time.time() - start_time < wait_time:
                        if vad_output > vad_threshold:
                            break

                    speaking = False
                    print("speaking:", speaking)                    
                    
            else:
                if vad_output > vad_threshold:
                    speaking = True
                    print("speaking:", speaking)
                    consecutive_below_threshold = 0

