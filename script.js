const activateButton = document.querySelector('#activate');
const sendButton = document.querySelector('#send');
let isRecording = false;
let mediaRecorder;

activateButton.addEventListener('click', () => {
    console.log('Activate button clicked.');
    if (isRecording) {
        console.log('Microphone is already activated.');
        alert('Microphone is already activated.');
        return;
    }

    navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
        console.log('Microphone access granted.');
        console.log({ stream });

        if (!MediaRecorder.isTypeSupported('audio/webm')) {
            console.log('Browser does not support audio/webm.');
            return alert('Browser not supported');
        }

        mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm',
        });
        console.log('MediaRecorder created.');

        const socket = new WebSocket('wss://api.deepgram.com/v1/listen', [
            'token',
            '87d2d3f1ceaf2da21fe2975880013d45d2ef84b1',
        ]);
        console.log('WebSocket created.');

        socket.onopen = () => {
            console.log('WebSocket connection opened.');
            document.querySelector('#status').textContent = 'Connected';
            console.log({ event: 'onopen' });

            mediaRecorder.addEventListener('dataavailable', async (event) => {
                if (event.data.size > 0 && socket.readyState == 1) {
                    socket.send(event.data);
                }
            });

            mediaRecorder.start(1000);
            console.log('MediaRecorder started.');
        };

        socket.onmessage = (message) => {
            const received = JSON.parse(message.data);
            const transcript = received.channel.alternatives[0].transcript;
            if (transcript && received.is_final) {
                console.log('Final transcript received:', transcript);
                document.querySelector('#transcript').textContent += transcript + ' ';
            }
        };

        socket.onclose = () => {
            console.log('WebSocket connection closed.');
            console.log({ event: 'onclose' });
        };

        socket.onerror = (error) => {
            console.log('WebSocket error occurred.');
            console.log({ event: 'onerror', error });
        };
    }).catch(error => {
        console.error("Error accessing the microphone: ", error);
    });

    isRecording = true;
    console.log('Microphone recording started.');
});

sendButton.addEventListener('click', () => {
    console.log('Send button clicked.');
    const transcript = document.querySelector('#transcript').textContent;
    if (!transcript) {
        console.log('No transcript available to send.');
        alert('No transcript available to send.');
        return;
    }

    console.log('Sending transcript to the server.');
    fetch('http://127.0.0.1:5001/send_transcript', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ transcript }),
    })
    .then(response => response.json())
    .then(data => {
        console.log('Response received from server:', data.message);
        console.log('Server response content:', data.response);
        if (data.audio) {
            console.log('Audio data received from server.');
            const audio = new Audio(`data:audio/wav;base64,${data.audio}`);
            audio.play().then(() => {
                console.log('Audio playback started');
            }).catch(error => {
                console.error('Error playing audio:', error);
            });
        } else {
            console.log('No audio data received from server.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
});
