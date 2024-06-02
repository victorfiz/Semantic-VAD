document.addEventListener('DOMContentLoaded', function() {
    let isRecording = false;
    let mediaRecorder;
    let audioContext;
    let audioQueue = [];
    let allowAudio = true;

    // Button event listeners
    document.querySelector('#activate').addEventListener('click', activateMicrophone);
    document.querySelector('#send').addEventListener('click', sendTranscript);
    document.querySelector('#appendText').addEventListener('click', appendText);
    document.querySelector('#clearTranscript').addEventListener('click', clearTranscript);
    document.querySelector('#stopSpeech').addEventListener('click', stopSpeech);
    document.querySelector('#startSpeech').addEventListener('click', startSpeech);

    const randomSocket = io('http://127.0.0.1:5001');

    // Test random number generator
    randomSocket.on('new_number', function(data) {
        console.log(data.number);
    });

    document.getElementById('startRandomGen').onclick = function() {
        fetch('/send_num', { method: 'POST' })
            .then(response => response.json())
            .then(data => console.log(data.status))
            .catch(error => console.error('Error:', error));
    };

    // Activate microphone for audio recording
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

    // Initialize audio context
    function initializeAudioContext() {
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioContext.state === 'suspended') {
            audioContext.resume();
        }
    }

    // Stop audio output
    function stopSpeech() {
        allowAudio = false;
        console.log('Speech output stopped');
    }

    // Start audio output
    function startSpeech() {
        allowAudio = true;
        console.log('Speech output started');
    }

    // Send transcript to server
    function sendTranscript() {
        const transcript = document.querySelector('#transcript').textContent;
        const responseField = document.querySelector('#response');
        responseField.textContent = ''; // Clear previous responses

        initializeAudioContext();

        const socket = io('http://127.0.0.1:5001');

        socket.on('response', function(data) {
            if (data.text) {
                responseField.textContent += data.text;
                console.log('Text chunk received:', data.text);
            }
            if (data.done) {
                socket.disconnect();
            }
        });

        socket.on('audio', async function(data) {
            if (data.audio && allowAudio) {
                await queueAudio(base64ToArrayBuffer(data.audio));
            }
            if (data.done) {
                socket.disconnect();
            }
        });

        fetch('http://127.0.0.1:5001/send_text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: transcript }),
        })
        .catch(error => {
            console.error('Error:', error);
            responseField.textContent = 'An error occurred';
        });
    }

    // Queue audio data for playback
    async function queueAudio(audioBuffer) {
        audioQueue.push(audioBuffer);
        if (audioQueue.length === 1) {
            await playNextInQueue();
        }
    }

    // Play next audio buffer in the queue
    async function playNextInQueue() {
        if (audioQueue.length > 0 && allowAudio) {
            const buffer = audioQueue[0];
            try {
                const decodedData = await audioContext.decodeAudioData(buffer);
                const source = audioContext.createBufferSource();
                source.buffer = decodedData;
                source.connect(audioContext.destination);
                source.start(0);

                source.onended = () => {
                    audioQueue.shift();
                    playNextInQueue();
                };
            } catch (e) {
                console.error('Failed to decode audio data', e);
                audioQueue.shift();
                playNextInQueue();
            }
        } else if (audioQueue.length > 0 && !allowAudio) {
            audioQueue = [];
        }
    }

    // Convert base64 to ArrayBuffer
    function base64ToArrayBuffer(base64) {
        const binaryString = window.atob(base64);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return bytes.buffer;
    }

    // Append predefined text to transcript
    function appendText() {
        document.querySelector('#transcript').textContent += "Tell me a quick fact about mammals";
    }

    // Clear transcript content
    function clearTranscript() {
        document.querySelector('#transcript').textContent = '';
    }
});
