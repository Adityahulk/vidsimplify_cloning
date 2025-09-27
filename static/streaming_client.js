/**
 * JavaScript client for real-time video dubbing streaming API
 */
class StreamingDubbingClient {
    constructor(serverUrl = 'ws://localhost:8000') {
        this.serverUrl = serverUrl;
        this.websocket = null;
        this.sessionId = null;
        this.isConnected = false;
        this.isStreaming = false;
        
        // Callbacks
        this.onFrameReceived = null;
        this.onTranscriptionReceived = null;
        this.onStatsReceived = null;
        this.onError = null;
        this.onReady = null;
        
        // Statistics
        this.stats = {
            framesSent: 0,
            framesReceived: 0,
            audioChunksSent: 0,
            connectionTime: 0,
            fps: 0
        };
        
        this.startTime = 0;
    }
    
    async connect(sessionId = null) {
        try {
            if (!sessionId) {
                sessionId = `client_${Date.now()}`;
            }
            
            this.sessionId = sessionId;
            const url = `${this.serverUrl}/ws/stream/${sessionId}`;
            
            console.log(`Connecting to ${url}`);
            this.websocket = new WebSocket(url);
            
            return new Promise((resolve, reject) => {
                this.websocket.onopen = () => {
                    this.isConnected = true;
                    this.startTime = Date.now();
                    console.log(`Connected to streaming server with session ID: ${sessionId}`);
                    resolve(true);
                };
                
                this.websocket.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    this.isConnected = false;
                    if (this.onError) {
                        this.onError(`Connection failed: ${error}`);
                    }
                    reject(error);
                };
                
                this.websocket.onmessage = (event) => {
                    this.handleMessage(JSON.parse(event.data));
                };
                
                this.websocket.onclose = () => {
                    console.log('Connection closed by server');
                    this.isConnected = false;
                    this.isStreaming = false;
                };
            });
        } catch (error) {
            console.error(`Failed to connect: ${error}`);
            if (this.onError) {
                this.onError(`Connection failed: ${error}`);
            }
            return false;
        }
    }
    
    disconnect() {
        this.isConnected = false;
        this.isStreaming = false;
        
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        console.log('Disconnected from streaming server');
    }
    
    async configure(config) {
        if (!this.isConnected || !this.websocket) {
            throw new Error('Not connected to server');
        }
        
        const message = {
            type: 'config',
            ...config
        };
        
        this.websocket.send(JSON.stringify(message));
        console.log('Configuration sent to server');
    }
    
    async sendFrame(frameData) {
        if (!this.isConnected || !this.websocket) {
            return;
        }
        
        try {
            const message = {
                type: 'frame',
                frame_data: frameData,
                timestamp: Date.now()
            };
            
            this.websocket.send(JSON.stringify(message));
            this.stats.framesSent++;
        } catch (error) {
            console.error(`Error sending frame: ${error}`);
            if (this.onError) {
                this.onError(`Frame send error: ${error}`);
            }
        }
    }
    
    async sendAudio(audioData) {
        if (!this.isConnected || !this.websocket) {
            return;
        }
        
        try {
            const message = {
                type: 'audio',
                audio_data: audioData,
                timestamp: Date.now()
            };
            
            this.websocket.send(JSON.stringify(message));
            this.stats.audioChunksSent++;
        } catch (error) {
            console.error(`Error sending audio: ${error}`);
            if (this.onError) {
                this.onError(`Audio send error: ${error}`);
            }
        }
    }
    
    requestStats() {
        if (!this.isConnected || !this.websocket) {
            return;
        }
        
        const message = { type: 'get_stats' };
        this.websocket.send(JSON.stringify(message));
    }
    
    handleMessage(data) {
        switch (data.type) {
            case 'ready':
                console.log('Server ready for streaming');
                this.isStreaming = true;
                if (this.onReady) {
                    this.onReady();
                }
                break;
                
            case 'processed_frame':
                if (this.onFrameReceived) {
                    this.onFrameReceived(data.frame_data, data.timestamp);
                }
                this.stats.framesReceived++;
                break;
                
            case 'transcription':
                if (this.onTranscriptionReceived) {
                    this.onTranscriptionReceived(data);
                }
                break;
                
            case 'stats':
                if (this.onStatsReceived) {
                    this.onStatsReceived(data);
                }
                break;
                
            case 'error':
                const errorMsg = data.message || 'Unknown error';
                console.error(`Server error: ${errorMsg}`);
                if (this.onError) {
                    this.onError(errorMsg);
                }
                break;
                
            default:
                console.warn(`Unknown message type: ${data.type}`);
        }
    }
    
    getStats() {
        const currentTime = Date.now();
        const elapsedTime = (currentTime - this.startTime) / 1000;
        
        this.stats.connectionTime = elapsedTime;
        this.stats.fps = this.stats.framesReceived / elapsedTime;
        
        return { ...this.stats };
    }
}

/**
 * Webcam streaming utility
 */
class WebcamStreamer {
    constructor(fps = 30) {
        this.fps = fps;
        this.frameInterval = 1000 / fps;
        this.mediaStream = null;
        this.videoElement = null;
        this.isStreaming = false;
        this.lastFrameTime = 0;
        this.imageCapture = null;
    }
    
    async startCamera() {
        try {
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                video: { 
                    width: 640, 
                    height: 480, 
                    frameRate: this.fps 
                },
                audio: true
            });
            
            this.isStreaming = true;
            
            // Create image capture
            const videoTrack = this.mediaStream.getVideoTracks()[0];
            this.imageCapture = new ImageCapture(videoTrack);
            
            console.log('Camera started');
            return true;
        } catch (error) {
            console.error(`Failed to start camera: ${error}`);
            return false;
        }
    }
    
    async getFrame() {
        if (!this.isStreaming || !this.imageCapture) {
            return null;
        }
        
        const currentTime = Date.now();
        if (currentTime - this.lastFrameTime < this.frameInterval) {
            return null;
        }
        
        try {
            const frame = await this.imageCapture.grabFrame();
            
            // Convert frame to base64
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.width = frame.width;
            canvas.height = frame.height;
            ctx.drawImage(frame, 0, 0);
            
            return new Promise((resolve) => {
                canvas.toBlob((blob) => {
                    const reader = new FileReader();
                    reader.onload = () => {
                        const base64 = reader.result.split(',')[1];
                        resolve(base64);
                    };
                    reader.readAsDataURL(blob);
                }, 'image/jpeg', 0.8);
            });
        } catch (error) {
            console.error(`Error capturing frame: ${error}`);
            return null;
        }
    }
    
    stopCamera() {
        this.isStreaming = false;
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
        console.log('Camera stopped');
    }
}

/**
 * Audio streaming utility
 */
class AudioStreamer {
    constructor(sampleRate = 16000, chunkSize = 4096) {
        this.sampleRate = sampleRate;
        this.chunkSize = chunkSize;
        this.audioContext = null;
        this.processor = null;
        this.source = null;
        this.isStreaming = false;
    }
    
    async startAudio() {
        try {
            this.audioContext = new AudioContext();
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.source = this.audioContext.createMediaStreamSource(stream);
            
            this.processor = this.audioContext.createScriptProcessor(this.chunkSize, 1, 1);
            
            this.processor.onaudioprocess = (event) => {
                if (this.onAudioData) {
                    const audioData = event.inputBuffer.getChannelData(0);
                    const bytes = new Float32Array(audioData).buffer;
                    const base64 = btoa(String.fromCharCode(...new Uint8Array(bytes)));
                    this.onAudioData(base64);
                }
            };
            
            this.source.connect(this.processor);
            this.processor.connect(this.audioContext.destination);
            
            this.isStreaming = true;
            console.log('Audio streaming started');
            return true;
        } catch (error) {
            console.error(`Failed to start audio: ${error}`);
            return false;
        }
    }
    
    stopAudio() {
        this.isStreaming = false;
        if (this.processor) {
            this.processor.disconnect();
        }
        if (this.source) {
            this.source.disconnect();
        }
        if (this.audioContext) {
            this.audioContext.close();
        }
        console.log('Audio streaming stopped');
    }
}

/**
 * Example usage
 */
class StreamingDemo {
    constructor() {
        this.client = new StreamingDubbingClient();
        this.webcam = new WebcamStreamer();
        this.audio = new AudioStreamer();
        
        this.setupCallbacks();
        this.setupUI();
    }
    
    setupCallbacks() {
        // Client callbacks
        this.client.onReady = () => {
            this.updateStatus('Ready', 'connected');
            this.startStreaming();
        };
        
        this.client.onFrameReceived = (frameData, timestamp) => {
            this.displayProcessedFrame(frameData);
        };
        
        this.client.onTranscriptionReceived = (data) => {
            this.displayTranscription(data);
        };
        
        this.client.onStatsReceived = (data) => {
            this.displayStats(data);
        };
        
        this.client.onError = (error) => {
            this.updateStatus(`Error: ${error}`, 'error');
        };
        
        // Audio callback
        this.audio.onAudioData = (audioData) => {
            if (this.client.isConnected) {
                this.client.sendAudio(audioData);
            }
        };
    }
    
    setupUI() {
        // Create UI elements
        this.statusElement = document.getElementById('status') || this.createStatusElement();
        this.inputVideoElement = document.getElementById('inputVideo') || this.createVideoElement('input');
        this.outputVideoElement = document.getElementById('outputVideo') || this.createVideoElement('output');
        this.transcriptionElement = document.getElementById('transcription') || this.createTranscriptionElement();
        this.statsElement = document.getElementById('stats') || this.createStatsElement();
        
        // Setup controls
        this.setupControls();
    }
    
    createStatusElement() {
        const element = document.createElement('div');
        element.id = 'status';
        element.className = 'status disconnected';
        element.textContent = 'Disconnected';
        document.body.appendChild(element);
        return element;
    }
    
    createVideoElement(type) {
        const container = document.createElement('div');
        container.className = 'video-box';
        
        const title = document.createElement('h3');
        title.textContent = type === 'input' ? 'Input Stream' : 'Processed Stream';
        
        const video = document.createElement('video');
        video.id = `${type}Video`;
        video.autoplay = true;
        video.muted = type === 'input';
        
        container.appendChild(title);
        container.appendChild(video);
        
        const videoContainer = document.querySelector('.video-container') || 
                              document.querySelector('body');
        videoContainer.appendChild(container);
        
        return video;
    }
    
    createTranscriptionElement() {
        const element = document.createElement('div');
        element.id = 'transcription';
        element.className = 'transcription';
        element.innerHTML = '<h3>Transcription</h3><div id="transcriptionContent"></div>';
        document.body.appendChild(element);
        return element;
    }
    
    createStatsElement() {
        const element = document.createElement('div');
        element.id = 'stats';
        element.className = 'stats';
        document.body.appendChild(element);
        return element;
    }
    
    setupControls() {
        // Start button
        const startBtn = document.getElementById('startBtn');
        if (startBtn) {
            startBtn.onclick = () => this.start();
        }
        
        // Stop button
        const stopBtn = document.getElementById('stopBtn');
        if (stopBtn) {
            stopBtn.onclick = () => this.stop();
        }
    }
    
    async start() {
        try {
            this.updateStatus('Connecting...', 'connecting');
            
            // Connect to server
            if (!await this.client.connect()) {
                throw new Error('Failed to connect to server');
            }
            
            // Configure streaming
            const targetLang = document.getElementById('targetLang')?.value || 'es';
            await this.client.configure({
                target_language: targetLang,
                source_language: null,
                enable_voice_cloning: false,
                chunk_duration: 1.0,
                whisper_model: 'tiny'
            });
            
            // Start camera
            if (!await this.webcam.startCamera()) {
                throw new Error('Failed to start camera');
            }
            
            // Start audio
            await this.audio.startAudio();
            
            this.updateStatus('Streaming...', 'streaming');
            
        } catch (error) {
            console.error(`Error starting stream: ${error}`);
            this.updateStatus(`Error: ${error}`, 'error');
        }
    }
    
    async stop() {
        this.webcam.stopCamera();
        this.audio.stopAudio();
        this.client.disconnect();
        this.updateStatus('Disconnected', 'disconnected');
    }
    
    async startStreaming() {
        // Main streaming loop
        const streamLoop = async () => {
            while (this.client.isConnected) {
                // Send video frame
                const frameData = await this.webcam.getFrame();
                if (frameData) {
                    await this.client.sendFrame(frameData);
                }
                
                // Request stats periodically
                if (Date.now() % 5000 < 100) { // Every 5 seconds
                    this.client.requestStats();
                }
                
                await new Promise(resolve => setTimeout(resolve, 100)); // 10 FPS
            }
        };
        
        streamLoop();
    }
    
    displayProcessedFrame(frameData) {
        const img = new Image();
        img.onload = () => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);
            
            const stream = canvas.captureStream(30);
            this.outputVideoElement.srcObject = stream;
        };
        img.src = `data:image/jpeg;base64,${frameData}`;
    }
    
    displayTranscription(data) {
        const content = document.getElementById('transcriptionContent');
        if (content) {
            content.innerHTML = `
                <p><strong>Original:</strong> ${data.original || ''}</p>
                <p><strong>Translated:</strong> ${data.translated || ''}</p>
            `;
        }
    }
    
    displayStats(data) {
        this.statsElement.innerHTML = `
            <h3>Statistics</h3>
            <p>Server FPS: ${data.fps?.toFixed(2) || 0}</p>
            <p>Frames Processed: ${data.frames_processed || 0}</p>
            <p>Audio Chunks: ${data.audio_chunks_processed || 0}</p>
            <p>Processing Time: ${data.processing_time?.toFixed(2) || 0}ms</p>
        `;
    }
    
    updateStatus(message, type) {
        this.statusElement.textContent = message;
        this.statusElement.className = `status ${type}`;
    }
}

// Initialize demo when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.streamingDemo = new StreamingDemo();
});
