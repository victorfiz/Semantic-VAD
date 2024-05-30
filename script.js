let isRecording = false;
let mediaRecorder;

document.querySelector('#activate').addEventListener('click', activateMicrophone);
document.querySelector('#send').addEventListener('click', sendTranscript);
document.querySelector('#appendText').addEventListener('click', appendText);
document.querySelector('#clearTranscript').addEventListener('click', clearTranscript);

// Handle microphone activation
function activateMicrophone() {
    if (isRecording) return alert('Microphone is already activated.');

    navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
        if (!MediaRecorder.isTypeSupported('audio/webm')) return alert('Browser not supported');

        mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

        // Connect to WebSocket for streaming audio
        const socket = new WebSocket('wss://api.deepgram.com/v1/listen', [
            'token',
            '87d2d3f1ceaf2da21fe2975880013d45d2ef84b1',
        ]);

        socket.onopen = () => {
            document.querySelector('#status').textContent = 'Connected';

            // Send audio data to WebSocket
            mediaRecorder.addEventListener('dataavailable', (event) => {
                if (event.data.size > 0 && socket.readyState === 1) {
                    socket.send(event.data);
                }
            });

            mediaRecorder.start(1000);
        };

        // Handle received transcription data
        socket.onmessage = (message) => {
            const { channel: { alternatives }, is_final } = JSON.parse(message.data);
            if (alternatives[0].transcript && is_final) {
                document.querySelector('#transcript').textContent += alternatives[0].transcript + ' ';
            }
        };

        socket.onerror = (error) => console.error('WebSocket error:', error);
    }).catch(error => console.error("Microphone access error:", error));

    isRecording = true;
}

// Send transcript to the server
function sendTranscript() {
    const transcript = document.querySelector('#transcript').textContent;
    if (!transcript) return alert('No transcript available to send.');

    fetch('http://127.0.0.1:5001/send_transcript', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcript }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.audio) {
            // Play audio response from server
            const audio = new Audio(`data:audio/wav;base64,${data.audio}`);
            audio.play().catch(error => console.error('Audio playback error:', error));
        }
    })
    .catch(error => console.error('Error sending transcript:', error));
}

function appendText() {
    document.querySelector('#transcript').textContent += "Tell me a quick fact about mammals";
}

function clearTranscript() {
    document.querySelector('#transcript').textContent = '';
}
