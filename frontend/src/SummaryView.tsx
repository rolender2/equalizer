import React from 'react';

interface KeyMoment {
    quote: string;
    insight: string;
}

interface SummaryViewProps {
    summary: {
        strong_move?: string;
        missed_opportunity?: string;
        improvement_tip?: string;
        negotiation_score?: number;
        tactics_faced?: string[];
        key_moments?: KeyMoment[];
        expanded_insights?: string[];
        error?: string;
    };
    onClose: () => void;
}

const SummaryView: React.FC<SummaryViewProps> = ({ summary, onClose }) => {
    if (summary.error) {
        return (
            <div style={{
                background: 'rgba(0, 0, 0, 0.95)',
                border: '2px solid #ff4444',
                borderRadius: '12px',
                padding: '24px',
                minWidth: '350px',
                maxWidth: '500px',
                color: '#fff',
                fontFamily: 'monospace'
            }}>
                <h2 style={{ color: '#ff4444', margin: '0 0 16px 0' }}>⚠️ Summary Error</h2>
                <p>{summary.error}</p>
                <button onClick={onClose} style={{ marginTop: '16px', background: '#333', color: '#fff', border: '1px solid #666', borderRadius: '6px', padding: '8px 16px', cursor: 'pointer' }}>Close</button>
            </div>
        );
    }

    const getScoreColor = (score: number) => {
        if (score >= 80) return '#00ff41'; // Green
        if (score >= 50) return '#ffd700'; // Gold/Yellow
        return '#ff4444'; // Red
    };

    const score = summary.negotiation_score ?? 0;
    const scoreColor = getScoreColor(score);

    return (
        <div style={{
            background: 'rgba(10, 10, 10, 0.98)',
            border: `1px solid ${scoreColor}`,
            borderRadius: '16px',
            padding: '24px',
            width: '600px',
            maxHeight: '85vh',
            overflowY: 'auto',
            color: '#fff',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            boxShadow: '0 20px 50px rgba(0,0,0,0.8)',
            // @ts-ignore
            WebkitAppRegion: 'no-drag',
            pointerEvents: 'auto'
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid #333', paddingBottom: '15px' }}>
                <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 600 }}>📊 Session Report Card</h2>
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '32px', fontWeight: 'bold', color: scoreColor }}>{score}</div>
                    <div style={{ fontSize: '10px', textTransform: 'uppercase', color: '#888', letterSpacing: '1px' }}>Score</div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '24px' }}>
                <div style={{ background: 'rgba(0, 255, 65, 0.1)', padding: '12px', borderRadius: '8px', borderLeft: '3px solid #00ff41' }}>
                    <div style={{ color: '#00ff41', fontSize: '11px', fontWeight: 'bold', textTransform: 'uppercase', marginBottom: '4px' }}>Strong Move</div>
                    <div style={{ fontSize: '13px', lineHeight: '1.4' }}>{summary.strong_move || 'N/A'}</div>
                </div>
                <div style={{ background: 'rgba(255, 152, 0, 0.1)', padding: '12px', borderRadius: '8px', borderLeft: '3px solid #ff9800' }}>
                    <div style={{ color: '#ff9800', fontSize: '11px', fontWeight: 'bold', textTransform: 'uppercase', marginBottom: '4px' }}>Missed Opp</div>
                    <div style={{ fontSize: '13px', lineHeight: '1.4' }}>{summary.missed_opportunity || 'N/A'}</div>
                </div>
                <div style={{ background: 'rgba(33, 150, 243, 0.1)', padding: '12px', borderRadius: '8px', borderLeft: '3px solid #2196F3' }}>
                    <div style={{ color: '#2196F3', fontSize: '11px', fontWeight: 'bold', textTransform: 'uppercase', marginBottom: '4px' }}>Top Tip</div>
                    <div style={{ fontSize: '13px', lineHeight: '1.4' }}>{summary.improvement_tip || 'N/A'}</div>
                </div>
            </div>

            {summary.tactics_faced && summary.tactics_faced.length > 0 && (
                <div style={{ marginBottom: '24px' }}>
                    <h3 style={{ fontSize: '14px', textTransform: 'uppercase', color: '#888', marginBottom: '10px', letterSpacing: '1px' }}>Tactics Faced</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {summary.tactics_faced.map((tactic, i) => (
                            <div key={i} style={{ background: '#222', padding: '8px 12px', borderRadius: '6px', fontSize: '13px', borderLeft: '3px solid #666' }}>
                                {tactic}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {summary.key_moments && summary.key_moments.length > 0 && (
                <div style={{ marginBottom: '24px' }}>
                    <h3 style={{ fontSize: '14px', textTransform: 'uppercase', color: '#888', marginBottom: '10px', letterSpacing: '1px' }}>Key Moments</h3>
                    {summary.key_moments.map((moment, i) => (
                        <div key={i} style={{ marginBottom: '12px', background: '#1a1a1a', padding: '12px', borderRadius: '8px', border: '1px solid #333' }}>
                            <div style={{ fontStyle: 'italic', color: '#ccc', marginBottom: '6px', fontSize: '13px' }}>"{moment.quote}"</div>
                            <div style={{ color: '#888', fontSize: '12px' }}>💡 {moment.insight}</div>
                        </div>
                    ))}
                </div>
            )}

            {summary.expanded_insights && summary.expanded_insights.length > 0 && (
                <div style={{ marginBottom: '24px', opacity: 0.8 }}>
                    <h3 style={{ fontSize: '14px', textTransform: 'uppercase', color: '#888', marginBottom: '10px', letterSpacing: '1px' }}>Additional Notes</h3>
                    <ul style={{ paddingLeft: '20px', fontSize: '13px', color: '#ccc', lineHeight: '1.5' }}>
                        {summary.expanded_insights.map((note, i) => (
                            <li key={i}>{note}</li>
                        ))}
                    </ul>
                </div>
            )}

            <button
                onClick={onClose}
                style={{
                    width: '100%',
                    background: scoreColor,
                    color: '#000',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '12px',
                    fontSize: '14px',
                    fontWeight: 'bold',
                    cursor: 'pointer',
                    transition: 'opacity 0.2s'
                }}
            >
                Close Report
            </button>
        </div>
    );
};

export default SummaryView;
