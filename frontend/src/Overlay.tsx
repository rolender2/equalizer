import { useState, useEffect, useRef } from 'react';

// Electron IPC for receiving toggle events
const ipcRenderer = (window as any).require?.('electron')?.ipcRenderer;

const ADVICE_DURATION_MS = 8000;
const SAMPLE_RATE = 16000;

// Available coach personalities
const PERSONALITIES = [
    { id: 'tactical', name: 'Tactical', icon: '⚔️' },
    { id: 'diplomatic', name: 'Diplomatic', icon: '🤝' },
    { id: 'socratic', name: 'Socratic', icon: '🤔' },
    { id: 'aggressive', name: 'Power', icon: '💪' },
];

export default function Overlay() {
    const [advice, setAdvice] = useState<string | null>(null);
    const [status, setStatus] = useState<string>('connecting');
    const [isListening, setIsListening] = useState(true);
    const [personality, setPersonality] = useState('tactical');
    const socketRef = useRef<WebSocket | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const processorRef = useRef<ScriptProcessorNode | null>(null);

    // Listen for toggle shortcut from Electron main process
    useEffect(() => {
        if (ipcRenderer) {
            const handleToggle = () => {
                setIsListening(prev => !prev);
            };
            ipcRenderer.on('toggle-listening', handleToggle);
            return () => {
                ipcRenderer.removeListener('toggle-listening', handleToggle);
            };
        }
    }, []);

    // Handle pause/resume audio processing
    useEffect(() => {
        if (processorRef.current && audioContextRef.current) {
            if (isListening) {
                audioContextRef.current.resume();
            } else {
                audioContextRef.current.suspend();
            }
        }
    }, [isListening]);

    // Auto-dismiss logic
    useEffect(() => {
        if (advice) {
            const timer = setTimeout(() => {
                setAdvice(null);
            }, ADVICE_DURATION_MS);
            return () => clearTimeout(timer);
        }
    }, [advice]);

    // Cycle through personalities
    const cyclePersonality = () => {
        const currentIndex = PERSONALITIES.findIndex(p => p.id === personality);
        const nextIndex = (currentIndex + 1) % PERSONALITIES.length;
        const newPersonality = PERSONALITIES[nextIndex].id;
        setPersonality(newPersonality);

        // Send personality change to backend
        if (socketRef.current?.readyState === WebSocket.OPEN) {
            socketRef.current.send(JSON.stringify({
                type: 'personality',
                personality: newPersonality
            }));
        }
    };

    // Main Wiring: Mic -> Socket
    useEffect(() => {
        let processor: ScriptProcessorNode | null = null;
        let microphone: MediaStreamAudioSourceNode | null = null;
        let stream: MediaStream | null = null;

        const connect = async () => {
            try {
                const ws = new WebSocket('ws://127.0.0.1:8000/ws');
                socketRef.current = ws;

                await new Promise<void>((resolve, reject) => {
                    ws.onopen = () => {
                        console.log('WS Connected');
                        resolve();
                    };
                    ws.onerror = () => reject(new Error('WebSocket error'));
                });

                setStatus('connected');

                ws.onmessage = (event) => {
                    console.log('Message received:', event.data);
                    try {
                        const data = JSON.parse(event.data);
                        if (data.type === 'advice') {
                            setAdvice(data.content);
                        } else if (data.type === 'personality_changed') {
                            console.log('Personality confirmed:', data.personality);
                        }
                    } catch {
                        // Legacy: plain text advice (backwards compatibility)
                        setAdvice(event.data);
                    }
                };

                ws.onclose = () => setStatus('connecting');

                stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                const audioContext = new window.AudioContext({ sampleRate: SAMPLE_RATE });
                audioContextRef.current = audioContext;
                microphone = audioContext.createMediaStreamSource(stream);
                processor = audioContext.createScriptProcessor(4096, 1, 1);
                processorRef.current = processor;

                processor.onaudioprocess = (e) => {
                    if (ws.readyState === WebSocket.OPEN) {
                        const inputData = e.inputBuffer.getChannelData(0);
                        const pcmData = floatTo16BitPCM(inputData);
                        ws.send(pcmData);
                    }
                };

                microphone.connect(processor);
                processor.connect(audioContext.destination);

            } catch (err) {
                console.error('Error connecting:', err);
                setStatus('error');
            }
        };

        connect();

        return () => {
            if (socketRef.current) socketRef.current.close();
            if (audioContextRef.current) audioContextRef.current.close();
            if (microphone) microphone.disconnect();
            if (processor) processor.disconnect();
        };
    }, []);

    const floatTo16BitPCM = (input: Float32Array) => {
        const output = new Int16Array(input.length);
        for (let i = 0; i < input.length; i++) {
            const s = Math.max(-1, Math.min(1, input[i]));
            output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return output.buffer;
    };

    // Determine display status
    const getDisplayStatus = () => {
        if (!isListening) return 'paused';
        return status;
    };

    const displayStatus = getDisplayStatus();
    const currentPersonality = PERSONALITIES.find(p => p.id === personality);

    return (
        <div
            style={{
                // @ts-ignore - Electron-specific CSS property
                WebkitAppRegion: 'drag',
                position: 'fixed',
                top: '50px',
                right: '50px',
                backgroundColor: 'rgba(0, 0, 0, 0.95)',
                color: '#00ff41',
                padding: '24px 32px',
                borderRadius: '16px',
                fontSize: '24px',
                fontWeight: 'bold',
                fontFamily: 'monospace',
                boxShadow: `0 8px 32px ${!isListening ? 'rgba(255, 153, 0, 0.3)' : 'rgba(0, 255, 65, 0.3)'}`,
                border: `3px solid ${displayStatus === 'error' ? '#ff0000' : displayStatus === 'paused' ? '#ff9900' : displayStatus === 'connected' ? '#00ff41' : '#ff9900'}`,
                textAlign: 'center',
                minWidth: '450px',
                maxWidth: '600px',
                zIndex: 99999,
                cursor: 'move'
            }}>
            {displayStatus === 'error' && (
                <div style={{ color: '#ff0000', fontSize: '18px', marginBottom: '8px' }}>
                    ⚠️ CONNECTION ERROR
                </div>
            )}
            {displayStatus === 'connecting' && (
                <div style={{ color: '#ff9900', fontSize: '18px' }}>
                    ⏳ CONNECTING...
                </div>
            )}
            {displayStatus === 'paused' && (
                <div style={{ color: '#ff9900', fontSize: '18px' }}>
                    ⏸️ PAUSED (Ctrl+Shift+S to resume)
                </div>
            )}
            {displayStatus === 'connected' && !advice && (
                <div style={{ color: '#00ff41', fontSize: '18px' }}>
                    🎤 LISTENING... (Ctrl+Shift+S to pause)
                </div>
            )}
            {advice && isListening && (
                <div style={{ fontSize: '28px', marginTop: '8px' }}>
                    {advice.toUpperCase()}
                </div>
            )}

            {/* Personality Selector Button - Centered below status */}
            <button
                onClick={(e) => {
                    e.stopPropagation();
                    console.log('Personality button clicked');
                    cyclePersonality();
                }}
                onMouseDown={(e) => e.stopPropagation()}
                style={{
                    // @ts-ignore - Electron-specific CSS property
                    WebkitAppRegion: 'no-drag',
                    marginTop: '12px',
                    background: 'rgba(255, 255, 255, 0.1)',
                    border: '1px solid rgba(0, 255, 65, 0.4)',
                    borderRadius: '6px',
                    padding: '4px 14px',
                    color: '#00ff41',
                    fontSize: '13px',
                    cursor: 'pointer',
                    fontFamily: 'monospace',
                    pointerEvents: 'auto',
                }}
                title="Click to change coaching style"
            >
                {currentPersonality?.icon} {currentPersonality?.name}
            </button>
        </div>
    );
}
