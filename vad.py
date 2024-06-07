import numpy as np
from collections import deque
import torch
import torchaudio
import time
from eos_prob import calculate_end_tokens_prob

torch.set_num_threads(1)

audio_buffer = deque(maxlen=44100 * 5)
data_transmission_started = False
vad_threshold = 0.35
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
    global audio_buffer, data_transmission_started
    global speaking, eos_prob
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
            
            # print(f"vad:{vad_output:.3f}")
            print(f"{'#' * (int(vad_output * 10)+1)}")

            if transcript != previous_transcript:
                previous_transcript = transcript
                print(f"trans: {transcript}")
                cleaned_transcript = transcript.rstrip()
                start_time = time.time()
                eos_prob, top_tokens = calculate_end_tokens_prob(cleaned_transcript)
                print(f"log_prob time: {(time.time() - start_time):.2f}")
                eos_prob += 0.001
                print(f"{eos_prob:.2f}")
                # print(f"{eos_prob} eos_prob for trans: {transcript}")

                wait_time = ((2 /(eos_prob ** 0.5))-2)
                wait_time = min(wait_time, 4)
                # print(f"Waiting for {wait_time:.2f} seconds. {log_probs_time:.2f} waited already. eos: {eos_prob} with {top_tokens}")

                while time.time() - start_time < wait_time:
                    if vad_output > vad_threshold:
                        print("broken")
                        return
                    time.sleep(0.1)

                speaking = False
                print("speaking:", speaking)                   
                
            if not speaking:
                if vad_output > vad_threshold:
                    speaking = True
                    print("speaking:", speaking)



