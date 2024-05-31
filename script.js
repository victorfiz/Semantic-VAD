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

// Handle audio response
let audioContext;
let audioQueue = [];

function initializeAudioContext() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioContext.state === 'suspended') {
        audioContext.resume();
    }
}

function sendTranscript() {
    const transcript = document.querySelector('#transcript').textContent;
    const response = document.querySelector('#response').textContent;
    const responseField = document.querySelector('#response');
    responseField.textContent = '';  // Clear previous responses

    // Ensure the AudioContext is created or resumed after a user gesture
    initializeAudioContext();

    // Establish WebSocket connection
    const socket = io('http://127.0.0.1:5001');

    socket.on('response', function(data) {
        if (data.text) {
            responseField.textContent += data.text; // Append text chunk to the paragraph
            console.log('Text chunk received:', data.text); // Log text chunk
        }
        if (data.done) {
            socket.disconnect();
        }
    });

    socket.on('audio', async function(data) {
        if (data.audio) {
            await queueAudio(base64ToArrayBuffer(data.audio));
        }
        if (data.done) {
            socket.disconnect();
        }
    });

    fetch('http://127.0.0.1:5001/send_text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: transcript, response: response}),
    })
    .catch(error => {
        console.error('Error:', error);
        responseField.textContent = 'An error occurred';
    });
}

async function queueAudio(audioBuffer) {
    audioQueue.push(audioBuffer);
    if (audioQueue.length === 1) {
        await playNextInQueue();
    }
}

async function playNextInQueue() {
    if (audioQueue.length > 0) {
        const buffer = audioQueue[0];
        try {
            const decodedData = await audioContext.decodeAudioData(buffer);
            const source = audioContext.createBufferSource();
            source.buffer = decodedData;
            source.connect(audioContext.destination);
            source.start(0);

            source.onended = () => {
                audioQueue.shift(); // Remove the played audio buffer
                playNextInQueue();  // Play the next audio buffer in the queue
            };
        } catch (e) {
            console.error('Failed to decode audio data', e);
            audioQueue.shift(); // Remove the problematic audio buffer
            playNextInQueue();  // Try the next audio buffer in the queue
        }
    }
}

function base64ToArrayBuffer(base64) {
    const binaryString = window.atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
}

function appendText() {
    document.querySelector('#transcript').textContent += "Tell me a quick fact about mammals";
}

function clearTranscript() {
    document.querySelector('#transcript').textContent = '';
}


