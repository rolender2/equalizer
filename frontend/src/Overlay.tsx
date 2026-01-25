import { useState, useEffect, useRef } from 'react';
import OutcomeModal from './OutcomeModal';
import PreFlight from './PreFlight';
import SummaryView from './SummaryView';

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

// Audio Level Meter Component
function AudioMeter({ level, label }: { level: number; label: string }) {
    const barCount = 8;
    const activeCount = Math.round(level * barCount);

    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px' }}>
            <span style={{ opacity: 0.7, minWidth: '24px' }}>{label}</span>
            <div style={{ display: 'flex', gap: '2px' }}>
                {Array.from({ length: barCount }).map((_, i) => (
                    <div
                        key={i}
                        style={{
                            width: '4px',
                            height: '12px',
                            backgroundColor: i < activeCount
                                ? (i > barCount * 0.7 ? '#ff4444' : '#00ff41')
                                : 'rgba(255, 255, 255, 0.2)',
                            borderRadius: '1px',
                            transition: 'background-color 0.1s',
                        }}
                    />
                ))}
            </div>
        </div>
    );
}

export default function Overlay() {
    const [advice, setAdvice] = useState<string | null>(null);
    const [status, setStatus] = useState<string>('init'); // 'init' | 'connecting' | 'connected' | 'paused' | 'error'
    const [isListening, setIsListening] = useState(true);
    const [personality, setPersonality] = useState('tactical');
    const [negotiationType, setNegotiationType] = useState('General');
    const [hasSystemAudio, setHasSystemAudio] = useState(false);
    const [micLevel, setMicLevel] = useState(0);
    const [systemLevel, setSystemLevel] = useState(0);
    const [skipSystemAudio, setSkipSystemAudio] = useState(() => {
        // Load preference from localStorage
        return localStorage.getItem('skipSystemAudio') === 'true';
    });

    // MVP Tightening: Negotiation Type
    const [hasSelectedType, setHasSelectedType] = useState(false);

    // MVP Tightening: Outcome Tagging
    const [sessionId, setSessionId] = useState<string>('');
    const [showOutcomeModal, setShowOutcomeModal] = useState(false);

    // Phase 4: Reflection Summary
    const [showSummary, setShowSummary] = useState(false);
    const [summaryData, setSummaryData] = useState<any>(null);

    const socketRef = useRef<WebSocket | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const processorRef = useRef<ScriptProcessorNode | null>(null);
    const micAnalyserRef = useRef<AnalyserNode | null>(null);
    const systemAnalyserRef = useRef<AnalyserNode | null>(null);
    const animationRef = useRef<number | null>(null);

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

    // Audio level meter animation loop
    useEffect(() => {
        const updateLevels = () => {
            if (micAnalyserRef.current) {
                const dataArray = new Uint8Array(micAnalyserRef.current.frequencyBinCount);
                micAnalyserRef.current.getByteFrequencyData(dataArray);
                const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
                setMicLevel(average / 255);
            }
            if (systemAnalyserRef.current) {
                const dataArray = new Uint8Array(systemAnalyserRef.current.frequencyBinCount);
                systemAnalyserRef.current.getByteFrequencyData(dataArray);
                const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
                setSystemLevel(average / 255);
            }
            animationRef.current = requestAnimationFrame(updateLevels);
        };

        if (status === 'connected') {
            updateLevels();
        }

        return () => {
            if (animationRef.current) {
                cancelAnimationFrame(animationRef.current);
            }
        };
    }, [status]);

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

    // Request system audio capture
    const requestSystemAudio = async (): Promise<MediaStream | null> => {
        try {
            // Use getDisplayMedia with audio to capture system/tab audio
            const stream = await navigator.mediaDevices.getDisplayMedia({
                video: { width: 1, height: 1 }, // Minimal video (required but we don't use it)
                audio: true
            });

            // Stop the video track immediately - we only want audio
            stream.getVideoTracks().forEach(track => track.stop());

            const audioTracks = stream.getAudioTracks();
            if (audioTracks.length > 0) {
                console.log('System audio captured:', audioTracks[0].label);
                setHasSystemAudio(true);
                return stream;
            } else {
                console.log('No audio track in display media');
                return null;
            }
        } catch (err) {
            console.log('System audio not available or denied:', err);
            return null;
        }
    };

    // Start the connection with audio
    const startConnection = async (withSystemAudio: boolean) => {
        setStatus('connecting');

        let processor: ScriptProcessorNode | null = null;
        let micSource: MediaStreamAudioSourceNode | null = null;
        let systemSource: MediaStreamAudioSourceNode | null = null;
        let micStream: MediaStream | null = null;
        let systemStream: MediaStream | null = null;

        try {
            const ws = new WebSocket('ws://127.0.0.1:8000/ws');
            socketRef.current = ws;

            await new Promise<void>((resolve, reject) => {
                ws.onopen = () => {
                    console.log('WS Connected');
                    console.log('Sending config with type:', negotiationType, 'personality:', personality);
                    // Send initial configuration
                    ws.send(JSON.stringify({
                        type: 'config',
                        negotiation_type: negotiationType,
                        personality: personality
                    }));
                    resolve();
                };
                ws.onerror = () => reject(new Error('WebSocket error'));
            });

            ws.onmessage = (event) => {
                console.log('Message received:', event.data);
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'advice') {
                        setAdvice(data.content);
                    } else if (data.type === 'session_init') {
                        setSessionId(data.session_id);
                        console.log('Session ID:', data.session_id);
                    } else if (data.type === 'personality_changed') {
                        console.log('Personality confirmed:', data.personality);
                    }
                } catch {
                    // Legacy: plain text advice (backwards compatibility)
                    setAdvice(event.data);
                }
            };

            ws.onclose = () => setStatus('connecting');

            // Create audio context
            const audioContext = new window.AudioContext({ sampleRate: SAMPLE_RATE });
            await audioContext.resume();
            audioContextRef.current = audioContext;

            // Create analysers for level meters
            const micAnalyser = audioContext.createAnalyser();
            micAnalyser.fftSize = 256;
            micAnalyserRef.current = micAnalyser;

            // Create a merger to combine mic + system audio
            const merger = audioContext.createChannelMerger(2);

            // Get microphone audio
            micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            micSource = audioContext.createMediaStreamSource(micStream);
            micSource.connect(micAnalyser);

            // Try to get system audio if requested
            if (withSystemAudio) {
                systemStream = await requestSystemAudio();
                if (systemStream && systemStream.getAudioTracks().length > 0) {
                    systemSource = audioContext.createMediaStreamSource(systemStream);

                    const systemAnalyser = audioContext.createAnalyser();
                    systemAnalyser.fftSize = 256;
                    systemAnalyserRef.current = systemAnalyser;
                    systemSource.connect(systemAnalyser);
                }
            }

            // Create processor for audio processing
            processor = audioContext.createScriptProcessor(4096, 2, 1);
            processorRef.current = processor;

            // Connect sources to merger
            micSource.connect(merger, 0, 0);
            if (systemSource) {
                systemSource.connect(merger, 0, 1);
            }

            // Connect merger to processor
            merger.connect(processor);
            processor.connect(audioContext.destination);

            processor.onaudioprocess = (e) => {
                if (ws.readyState === WebSocket.OPEN) {
                    // Mix channels if we have both, otherwise just use what we have
                    const channel0 = e.inputBuffer.getChannelData(0);
                    const channel1 = e.inputBuffer.numberOfChannels > 1
                        ? e.inputBuffer.getChannelData(1)
                        : channel0;

                    // Simple mix: average the two channels
                    const mixed = new Float32Array(channel0.length);
                    for (let i = 0; i < channel0.length; i++) {
                        mixed[i] = (channel0[i] + channel1[i]) / 2;
                    }

                    const pcmData = floatTo16BitPCM(mixed);
                    ws.send(pcmData);
                }
            };

            setStatus('connected');

        } catch (err) {
            console.error('Error connecting:', err);
            setStatus('error');
        }
    };

    // Handle skip preference
    const handleSkip = () => {
        localStorage.setItem('skipSystemAudio', 'true');
        setSkipSystemAudio(true);
        startConnection(false);
    };

    const handleShareAudio = () => {
        startConnection(true);
    };

    // Auto-start if skip preference is set
    useEffect(() => {
        if (skipSystemAudio && status === 'init' && hasSelectedType) {
            startConnection(false);
        }
    }, [skipSystemAudio, status, hasSelectedType]);

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

    // 1. Pre-flight: Select Negotiation Type
    if (status === 'init' && !hasSelectedType) {
        return (
            <PreFlight
                onStart={({ type }) => {
                    setNegotiationType(type);
                    setHasSelectedType(true);
                }}
            />
        );
    }

    // 2. Initial Audio Setup (if not auto-skipping)
    if (status === 'init' && !skipSystemAudio) {
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
                    fontSize: '18px',
                    fontWeight: 'bold',
                    fontFamily: 'monospace',
                    boxShadow: '0 8px 32px rgba(0, 255, 65, 0.3)',
                    border: '3px solid #00ff41',
                    textAlign: 'center',
                    minWidth: '350px',
                    zIndex: 99999,
                    cursor: 'move'
                }}>
                <div style={{ marginBottom: '16px' }}>🎤 SIDEKICK READY</div>
                <div style={{ fontSize: '13px', color: '#888', marginBottom: '4px' }}>
                    Scenario: <span style={{ color: '#fff' }}>{negotiationType}</span>
                </div>
                <div style={{ fontSize: '12px', opacity: 0.8, marginBottom: '16px' }}>
                    Capture system audio to hear both sides of calls
                </div>
                <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
                    <button
                        onClick={(e) => { e.stopPropagation(); console.log('Share clicked'); handleShareAudio(); }}
                        onMouseDown={(e) => e.stopPropagation()}
                        style={{
                            // @ts-ignore
                            WebkitAppRegion: 'no-drag',
                            background: '#00ff41',
                            color: '#000',
                            border: 'none',
                            borderRadius: '6px',
                            padding: '8px 16px',
                            fontSize: '14px',
                            fontWeight: 'bold',
                            cursor: 'pointer',
                            fontFamily: 'monospace',
                            pointerEvents: 'auto',
                        }}
                    >
                        🔊 Share Audio
                    </button>
                    <button
                        onClick={(e) => { e.stopPropagation(); console.log('Skip clicked'); handleSkip(); }}
                        onMouseDown={(e) => e.stopPropagation()}
                        style={{
                            // @ts-ignore
                            WebkitAppRegion: 'no-drag',
                            background: 'transparent',
                            color: '#00ff41',
                            border: '1px solid #00ff41',
                            borderRadius: '6px',
                            padding: '8px 16px',
                            fontSize: '14px',
                            cursor: 'pointer',
                            fontFamily: 'monospace',
                            pointerEvents: 'auto',
                        }}
                    >
                        Skip
                    </button>
                    <button
                        onClick={(e) => { e.stopPropagation(); setHasSelectedType(false); }}
                        onMouseDown={(e) => e.stopPropagation()}
                        style={{
                            // @ts-ignore
                            WebkitAppRegion: 'no-drag',
                            background: 'transparent',
                            color: '#666',
                            border: '1px solid #444',
                            borderRadius: '6px',
                            padding: '8px 12px',
                            fontSize: '14px',
                            cursor: 'pointer',
                            fontFamily: 'monospace',
                            pointerEvents: 'auto',
                        }}
                    >
                        Back
                    </button>
                </div>
                <div style={{ fontSize: '10px', opacity: 0.5, marginTop: '12px' }}>
                    Skip = Mic only (use for quick tests)
                </div>
            </div>
        );
    }

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
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            setShowOutcomeModal(true);
                        }}
                        onMouseDown={(e) => e.stopPropagation()}
                        style={{
                            display: 'block',
                            margin: '12px auto 0',
                            // @ts-ignore
                            WebkitAppRegion: 'no-drag',
                            background: '#ff4444',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            padding: '6px 12px',
                            fontSize: '14px',
                            cursor: 'pointer',
                            pointerEvents: 'auto'
                        }}
                    >
                        End Session & Save
                    </button>
                </div>
            )}
            {displayStatus === 'connected' && !advice && (
                <div style={{ color: '#00ff41', fontSize: '18px' }}>
                    🎤 LISTENING... {hasSystemAudio ? '🔊' : ''}
                    <div style={{ fontSize: '12px', marginTop: '4px', opacity: 0.7 }}>
                        {hasSystemAudio ? 'Mic + System Audio' : 'Mic Only'} • Ctrl+Shift+S to pause
                    </div>
                    <div style={{ fontSize: '11px', marginTop: '2px', color: '#888' }}>
                        Scenario: <span style={{ color: '#fff' }}>{negotiationType}</span>
                    </div>
                    {/* Audio Level Meters */}
                    <div style={{
                        display: 'flex',
                        justifyContent: 'center',
                        gap: '20px',
                        marginTop: '10px'
                    }}>
                        <AudioMeter level={micLevel} label="🎤" />
                        {hasSystemAudio && <AudioMeter level={systemLevel} label="🔊" />}
                    </div>

                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            // Pause first, then show modal
                            setIsListening(false);
                            setShowOutcomeModal(true);
                        }}
                        onMouseDown={(e) => e.stopPropagation()}
                        style={{
                            // @ts-ignore
                            WebkitAppRegion: 'no-drag',
                            marginTop: '16px',
                            background: 'transparent',
                            color: '#ff4444',
                            border: '1px solid #ff4444',
                            borderRadius: '6px',
                            padding: '4px 8px',
                            fontSize: '11px',
                            cursor: 'pointer',
                            pointerEvents: 'auto',
                            opacity: 0.8
                        }}
                    >
                        ⏹️ End Session
                    </button>
                </div>
            )}
            {advice && isListening && (
                <div style={{ marginTop: '16px', textAlign: 'center' }}>
                    {advice.split('\n').map((line, i) => (
                        <div key={i} style={{
                            fontSize: i === 0 ? '16px' : '14px',
                            fontWeight: i === 0 ? 'bold' : 'normal',
                            color: i === 0 ? '#00ff00' : '#cccccc',
                            marginBottom: i === 0 ? '8px' : '4px',
                            textAlign: i === 0 ? 'center' : 'left',
                            paddingLeft: i === 0 ? 0 : '10px'
                        }}>
                            {line.toUpperCase()}
                        </div>
                    ))}
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
            {showOutcomeModal && sessionId && (
                <OutcomeModal
                    onClose={() => setShowOutcomeModal(false)}
                    onSave={async (data) => {
                        try {
                            console.log(`Saving to: http://127.0.0.1:8000/sessions/${sessionId}/outcome`);
                            const response = await fetch(`http://127.0.0.1:8000/sessions/${sessionId}/outcome`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify(data)
                            });
                            if (!response.ok) {
                                const errText = await response.text();
                                throw new Error(`Server returned ${response.status}: ${errText}`);
                            }
                            console.log('Outcome saved');

                            // Generate reflection summary
                            try {
                                const summaryRes = await fetch(`http://127.0.0.1:8000/sessions/${sessionId}/summary`, {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' }
                                });
                                if (summaryRes.ok) {
                                    const summary = await summaryRes.json();
                                    setSummaryData(summary);
                                    setShowOutcomeModal(false);
                                    setShowSummary(true);
                                    return; // Don't reset yet, show summary first
                                }
                            } catch (sumErr) {
                                console.error('Summary generation failed:', sumErr);
                            }

                            // If summary fails, just reset
                            alert('Outcome Saved Successfully!');
                            setShowOutcomeModal(false);
                            setStatus('init');
                            setIsListening(true);
                            setHasSelectedType(false);
                            setAdvice(null);
                        } catch (err: any) {
                            console.error(err);
                            alert(`Failed to save outcome: ${err.message}`);
                        }
                    }}
                />
            )}

            {/* Phase 4: Reflection Summary */}
            {showSummary && summaryData && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    background: 'rgba(0, 0, 0, 0.7)',
                    zIndex: 1000,
                    // @ts-ignore
                    WebkitAppRegion: 'no-drag',
                    pointerEvents: 'auto'
                }}>
                    <SummaryView
                        summary={summaryData}
                        onClose={() => {
                            setShowSummary(false);
                            setSummaryData(null);
                            setStatus('init');
                            setIsListening(true);
                            setHasSelectedType(false);
                            setAdvice(null);
                        }}
                    />
                </div>
            )}
        </div>
    );
}
