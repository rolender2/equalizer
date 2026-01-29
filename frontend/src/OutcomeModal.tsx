import { useState } from 'react';

type OutcomeResult = 'won' | 'lost' | 'deferred';

interface OutcomeData {
    result: OutcomeResult;
    confidence: number;
    notes: string;
    expanded_debrief: boolean;
}

interface OutcomeModalProps {
    onSave: (data: OutcomeData) => Promise<void>;
    onClose: () => void;
}

export default function OutcomeModal({ onSave, onClose }: OutcomeModalProps) {
    const [result, setResult] = useState<OutcomeResult | null>(null);
    const [confidence, setConfidence] = useState<number>(3);
    const [notes, setNotes] = useState('');
    const [expandedDebrief, setExpandedDebrief] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async () => {
        if (!result) return;

        setIsSubmitting(true);
        try {
            await onSave({ result, confidence, notes, expanded_debrief: expandedDebrief });
        } catch (err) {
            console.error('Failed to save outcome:', err);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.85)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100000,
            backdropFilter: 'blur(5px)',
            // @ts-ignore
            WebkitAppRegion: 'no-drag',
            cursor: 'default',
            pointerEvents: 'auto'
        }}>
            <div style={{
                // @ts-ignore
                WebkitAppRegion: 'no-drag',
                backgroundColor: '#1a1a1a',
                border: '1px solid #333',
                borderRadius: '12px',
                padding: '24px',
                width: '400px',
                color: '#fff',
                display: 'flex',
                flexDirection: 'column',
                gap: '20px',
                boxShadow: '0 10px 40px rgba(0,0,0,0.5)'
            }}>
                {/* @ts-ignore */}
                <h2 style={{
                    margin: 0,
                    fontSize: '20px',
                    textAlign: 'center',
                    WebkitAppRegion: 'drag',
                    cursor: 'move',
                    padding: '10px'
                }}>
                    Session Outcome
                </h2>

                {/* Result Selection */}
                <div style={{ display: 'flex', gap: '10px' }}>
                    <button
                        onClick={() => setResult('won')}
                        style={{
                            flex: 1,
                            padding: '12px',
                            backgroundColor: result === 'won' ? '#00ff41' : '#333',
                            color: result === 'won' ? '#000' : '#fff',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontWeight: 'bold',
                            fontSize: '13px',
                            transition: 'all 0.2s'
                        }}
                    >
                        Favorable
                    </button>
                    <button
                        onClick={() => setResult('lost')}
                        style={{
                            flex: 1,
                            padding: '12px',
                            backgroundColor: result === 'lost' ? '#ff4444' : '#333',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontWeight: 'bold',
                            fontSize: '13px',
                            transition: 'all 0.2s',
                            opacity: result === 'lost' ? 1 : 0.8
                        }}
                    >
                        Unfavorable
                    </button>
                    <button
                        onClick={() => setResult('deferred')}
                        style={{
                            flex: 1,
                            padding: '12px',
                            backgroundColor: result === 'deferred' ? '#888' : '#333',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontWeight: 'bold',
                            fontSize: '13px',
                            transition: 'all 0.2s'
                        }}
                    >
                        Pending
                    </button>
                </div>

                {/* Confidence Slider */}
                <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '14px', opacity: 0.8 }}>
                        <span>Confidence</span>
                        <span>{confidence}/5</span>
                    </div>
                    <input
                        type="range"
                        min="1"
                        max="5"
                        value={confidence}
                        onChange={(e) => setConfidence(parseInt(e.target.value))}
                        style={{ width: '100%', cursor: 'pointer', accentColor: '#00ff41' }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', opacity: 0.5, marginTop: '4px' }}>
                        <span>Unsure</span>
                        <span>Certain</span>
                    </div>
                </div>

                {/* Notes */}
                <textarea
                    placeholder="Key takeaways or blockers..."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    style={{
                        width: '100%',
                        height: '80px',
                        backgroundColor: '#222',
                        border: '1px solid #444',
                        borderRadius: '6px',
                        padding: '10px',
                        color: '#fff',
                        resize: 'none',
                        fontFamily: 'inherit'
                    }}
                />

                <div style={{ fontSize: '10px', color: '#666', textAlign: 'center', marginTop: '-10px', marginBottom: '5px' }}>
                    This is for personal reflection only
                </div>

                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#aaa' }}>
                    <input
                        type="checkbox"
                        checked={expandedDebrief}
                        onChange={(e) => setExpandedDebrief(e.target.checked)}
                    />
                    Include Expanded Debrief (more detail)
                </label>

                {/* Actions */}
                <div style={{ display: 'flex', gap: '10px' }}>
                    <button
                        onClick={onClose}
                        style={{
                            flex: 1,
                            padding: '10px',
                            backgroundColor: 'transparent',
                            border: '1px solid #444',
                            color: '#888',
                            borderRadius: '6px',
                            cursor: 'pointer'
                        }}
                    >
                        Skip
                    </button>
                    <button
                        onClick={handleSubmit}
                        disabled={!result || isSubmitting}
                        style={{
                            flex: 1,
                            padding: '10px',
                            backgroundColor: result ? '#00ff41' : '#444',
                            color: result ? '#000' : '#888',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: result ? 'pointer' : 'not-allowed',
                            fontWeight: 'bold'
                        }}
                    >
                        {isSubmitting ? 'Saving...' : 'Save Outcome'}
                    </button>
                </div>
            </div>
        </div>
    );
}
