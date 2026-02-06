
import { useEffect, useState } from 'react';

interface SessionSummary {
    session_id: string;
    timestamp: string;
    negotiation_type: string;
    negotiation_score: number;
    outcome?: string;
    duration_seconds: number;
}

interface Props {
    onBack: () => void;
    onSelectSession: (sessionId: string) => void;
}

export default function SessionHistory({ onBack, onSelectSession }: Props) {
    const [sessions, setSessions] = useState<SessionSummary[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('http://127.0.0.1:8000/sessions')
            .then(res => res.json())
            .then(data => {
                setSessions(data.sessions || []);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, []);

    const formatTime = (isoString: string) => {
        return new Date(isoString).toLocaleString('en-US', {
            month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'
        });
    };

    const formatDuration = (seconds: number) => {
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${m}m ${s}s`;
    };

    const getScoreColor = (score: number) => {
        if (score >= 80) return '#00ff41';
        if (score >= 60) return '#ff9900';
        return '#ff4444';
    };

    return (
        <div style={{
            // @ts-ignore
            WebkitAppRegion: 'drag',
            width: '100%',
            height: '100%',
            backgroundColor: 'rgba(0, 0, 0, 0.95)',
            color: '#00ff41',
            borderRadius: '16px',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            border: '1px solid #333'
        }}>
            {/* Header */}
            <div style={{
                padding: '16px 24px',
                borderBottom: '1px solid #333',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                background: 'rgba(0,0,0,0.5)'
            }}>
                <div style={{ fontSize: '18px', fontWeight: 'bold' }}>📜 Past Sessions</div>
                <button
                    onClick={(e) => { e.stopPropagation(); onBack(); }}
                    onMouseDown={(e) => e.stopPropagation()}
                    style={{
                        // @ts-ignore
                        WebkitAppRegion: 'no-drag',
                        background: 'transparent',
                        border: '1px solid #666',
                        color: '#888',
                        borderRadius: '6px',
                        padding: '6px 12px',
                        cursor: 'pointer',
                        fontSize: '13px'
                    }}
                >
                    Back to Start
                </button>
            </div>

            {/* List */}
            <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
            }}>
                {loading ? (
                    <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>Loading history...</div>
                ) : sessions.length === 0 ? (
                    <div style={{ padding: '40px', textAlign: 'center', color: '#666' }}>
                        No sessions recorded yet.
                    </div>
                ) : (
                    sessions.map(session => (
                        <div
                            key={session.session_id}
                            onClick={(e) => {
                                e.stopPropagation();
                                onSelectSession(session.session_id);
                            }}
                            onMouseDown={(e) => e.stopPropagation()}
                            style={{
                                // @ts-ignore
                                WebkitAppRegion: 'no-drag',
                                background: 'rgba(255,255,255,0.05)',
                                borderRadius: '8px',
                                padding: '12px 16px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                transition: 'background 0.2s',
                                border: '1px solid transparent'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.borderColor = '#00ff41'}
                            onMouseLeave={(e) => e.currentTarget.style.borderColor = 'transparent'}
                        >
                            {/* Left: Info */}
                            <div>
                                <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#fff', marginBottom: '4px' }}>
                                    {session.negotiation_type || 'General'}
                                </div>
                                <div style={{ fontSize: '12px', color: '#888' }}>
                                    {formatTime(session.timestamp)} • {formatDuration(session.duration_seconds)}
                                </div>
                            </div>

                            {/* Right: Outcome/Score */}
                            <div style={{ textAlign: 'right' }}>
                                {session.negotiation_score > 0 && (
                                    <div style={{
                                        fontSize: '18px',
                                        fontWeight: 'bold',
                                        color: getScoreColor(session.negotiation_score)
                                    }}>
                                        {session.negotiation_score}
                                    </div>
                                )}
                                <div style={{
                                    fontSize: '11px',
                                    textTransform: 'uppercase',
                                    color: session.outcome === 'Won' ? '#00ff41' : (session.outcome === 'Lost' ? '#ff4444' : '#888')
                                }}>
                                    {session.outcome || 'N/A'}
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
