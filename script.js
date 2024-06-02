document.addEventListener('DOMContentLoaded', function() {
    let isRecording = false;
    let mediaRecorder;
    let audioContext;
    let audioQueue = [];
    let allowAudio = true;
    let keepAliveInterval;

    document.querySelector('#activate').addEventListener('click', activateMicrophone);
    document.querySelector('#send').addEventListener('click', sendTranscript);
    document.querySelector('#appendText').addEventListener('click', appendText);
    document.querySelector('#clearTranscript').addEventListener('click', clearTranscript);
    document.querySelector('#stopSpeech').addEventListener('click', stopSpeech);
    document.querySelector('#startSpeech').addEventListener('click', startSpeech);

    const vadSocket = io();

    vadSocket.on('vad_decision', function(data) {
        console.log(data.audio);
        console.log(data.transcript)
    });

    function captureMicrophoneAudio() {
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                createAudioContext();
                const source = audioContext.createMediaStreamSource(stream);
                const processor = audioContext.createScriptProcessor(4096, 1, 1);
                source.connect(processor);
                processor.connect(audioContext.destination);
                processor.onaudioprocess = function (e) {
                    const audioData = e.inputBuffer.getChannelData(0);
                    vadSocket.emit('vad_audio', { audio: audioData.buffer });
                };
            })
            .catch(err => console.error('Error accessing audio stream:', err));
    }    

    function activateMicrophone() {
        if (isRecording) return alert('Microphone is already activated.');
        navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
            if (!MediaRecorder.isTypeSupported('audio/webm')) return alert('Browser not supported');
            mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
            const socket = new WebSocket('wss://api.deepgram.com/v1/listen', ['token', '87d2d3f1ceaf2da21fe2975880013d45d2ef84b1']);
            socket.onopen = () => {
                document.querySelector('#status').textContent = 'Connected';
                mediaRecorder.addEventListener('dataavailable', (event) => {
                    if (event.data.size > 0 && socket.readyState === 1) {
                        socket.send(event.data);
                    }
                });
                mediaRecorder.start(1000);
            };
            socket.onmessage = (message) => {
                const { channel: { alternatives }, is_final } = JSON.parse(message.data);
                if (alternatives[0].transcript && is_final) {
                    const transcriptElement = document.querySelector('#transcript');
                    transcriptElement.textContent += alternatives[0].transcript + ' ';
                    vadSocket.emit('vad_audio', { transcript: transcriptElement.textContent });
                }
            };
            socket.onerror = (error) => console.error('WebSocket error:', error);
        }).catch(error => console.error("Microphone access error:", error));
        isRecording = true;
    }

    function createAudioContext() {
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            keepAliveInterval = setInterval(() => {
                if (audioContext.state === 'suspended') {
                    audioContext.resume(); 
                }
            }, 100);
        }
    }

    function stopSpeech() {
        allowAudio = false;
        console.log('Speech output stopped');
    }

    function startSpeech() {
        allowAudio = true;
        console.log('Speech output started');
    }

    function sendTranscript() {
        const transcript = document.querySelector('#transcript').textContent;
        const responseField = document.querySelector('#response');
        responseField.textContent = '';
        createAudioContext();
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
            body: JSON.stringify({ text: transcript, response: '' }),
        }).catch(error => {
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

    captureMicrophoneAudio();

    window.addEventListener('beforeunload', () => {
        clearInterval(keepAliveInterval);
        if (audioContext) {
            audioContext.close();
        }
    });
});
