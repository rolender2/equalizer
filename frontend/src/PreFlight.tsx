import { useState, useEffect } from 'react';

interface PreFlightProps {
    onStart: (config: { type: string; mode: 'live' | 'debrief'; test_mode_counterparty: boolean; emit_interim: boolean; endpointing_ms: number; window_size_seconds: number }) => void;
}

const TYPE_DESCRIPTIONS: Record<string, { label: string; desc: string }> = {
    "Vendor": { label: "Vendor Pricing", desc: "Pricing discussions, concessions, terms, or service-level pushback" },
    "Scope": { label: "Scope & Deliverables", desc: "Preventing scope creep, timeline pressure, or unpaid expansion" },
    "Renewal": { label: "Renewal / Upsell", desc: "Contract renewals, price increases, or expansion pressure" },
    "General": { label: "General Business Conversation", desc: "Professional discussions involving leverage or persuasion" },
    // "Salary": - Hidden for this persona
};

export default function PreFlight({ onStart }: PreFlightProps) {
    const [types, setTypes] = useState<string[]>([]);
    const [selectedType, setSelectedType] = useState<string>('Vendor'); // Default for this persona
    const [preset, setPreset] = useState<'practice' | 'live_call' | 'post_analysis'>('practice');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('http://127.0.0.1:8000/negotiation-types')
            .then(res => res.json())
            .then(data => {
                // Filter types to only those in our map (hides Salary if it's not in map)
                const backendTypes = data.types || [];
                const supportedTypes = backendTypes.filter((t: string) => t in TYPE_DESCRIPTIONS);

                // If "Vendor" is available, make it first, then others. Or just use backend order filtered.
                // We'll trust backend order but filter.
                setTypes(supportedTypes);

                // Load saved preference OR default to Vendor
                const saved = localStorage.getItem('lastNegotiationType');
                if (saved && supportedTypes.includes(saved)) {
                    setSelectedType(saved);
                } else if (supportedTypes.includes('Vendor')) {
                    setSelectedType('Vendor');
                } else if (supportedTypes.length > 0) {
                    setSelectedType(supportedTypes[0]);
                }

                setLoading(false);
            })
            .catch(err => {
                console.error('Failed to load types:', err);
                // Fallback
                setTypes(['General']);
                setLoading(false);
            });
    }, []);

    const handleStart = () => {
        localStorage.setItem('lastNegotiationType', selectedType);
        const presetConfig = {
            practice: { mode: 'live' as const, test_mode_counterparty: true, emit_interim: true, endpointing_ms: 200, window_size_seconds: 0 },
            live_call: { mode: 'live' as const, test_mode_counterparty: false, emit_interim: false, endpointing_ms: 300, window_size_seconds: 15 },
            post_analysis: { mode: 'debrief' as const, test_mode_counterparty: false, emit_interim: false, endpointing_ms: 300, window_size_seconds: 15 }
        };
        const cfg = presetConfig[preset];
        onStart({
            type: selectedType,
            mode: cfg.mode,
            test_mode_counterparty: cfg.test_mode_counterparty,
            emit_interim: cfg.emit_interim,
            endpointing_ms: cfg.endpointing_ms,
            window_size_seconds: cfg.window_size_seconds
        });
    };

    if (loading) return <div style={{ color: '#00ff41' }}>Loading scenarios...</div>;

    return (
        <div
            className="preflight-card"
            style={{
            // @ts-ignore
            backgroundColor: 'rgba(0, 0, 0, 0.95)',
            border: '2px solid #00ff41',
            borderRadius: '16px',
            padding: '16px',
            color: '#fff',
            minWidth: '460px',
            maxHeight: '90vh',
            overflowY: 'auto',
            scrollbarWidth: 'none',
            msOverflowStyle: 'none',
            textAlign: 'center',
            boxShadow: '0 8px 32px rgba(0, 255, 65, 0.2)',
            pointerEvents: 'auto'
        }}>
            <h2 style={{
                margin: '0 0 2px 0',
                fontSize: '16px',
                color: '#00ff41',
                // @ts-ignore
                WebkitAppRegion: 'drag',
                cursor: 'move',
                userSelect: 'none'
            }}>
                Set the context for this conversation
            </h2>
            <div style={{ fontSize: '11px', color: '#888', marginBottom: '8px' }}>
                This helps Sidekick recognize leverage and risk patterns.
            </div>

            <div style={{ marginBottom: '8px', textAlign: 'left' }}>
                <label style={{ display: 'block', fontSize: '11px', color: '#888', marginBottom: '4px', fontWeight: 'bold' }}>
                    Conversation Context
                </label>
                <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px'
                }}>
                    {types.map(type => {
                        const info = TYPE_DESCRIPTIONS[type];
                        return (
                            <button
                                key={type}
                                onClick={() => setSelectedType(type)}
                                style={{
                                    background: selectedType === type ? 'rgba(0, 255, 65, 0.15)' : '#222',
                                    border: `1px solid ${selectedType === type ? '#00ff41' : '#444'}`,
                                    padding: '8px',
                                    borderRadius: '6px',
                                    cursor: 'pointer',
                                    textAlign: 'left',
                                    transition: 'all 0.2s',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    gap: '1px'
                                }}
                            >
                                <div style={{
                                    color: selectedType === type ? '#00ff41' : '#eee',
                                    fontWeight: 'bold',
                                    fontSize: '13px',
                                    display: 'flex',
                                    justifyContent: 'space-between'
                                }}>
                                    {info?.label || type}
                                    {(type === 'Vendor' && selectedType === 'Vendor') && <span style={{ fontSize: '9px', opacity: 0.8 }}>(Recommended)</span>}
                                </div>
                                <div style={{
                                    color: '#888',
                                    fontSize: '10px',
                                    lineHeight: '1.2'
                                }}>
                                    {info?.desc || "Scenario"}
                                </div>
                            </button>
                        );
                    })}
                </div>
            </div>

            <div style={{ marginBottom: '8px', textAlign: 'left', background: '#222', padding: '8px', borderRadius: '8px' }}>
                <label style={{ display: 'block', fontSize: '11px', color: '#888', marginBottom: '4px', fontWeight: 'bold' }}>
                    Mode Preset
                </label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {[
                        { id: 'practice', label: 'Practice Mode', desc: 'Solo/YouTube demo. Fast, permissive detection.' },
                        { id: 'live_call', label: 'Live Call', desc: 'Two-party call. Real-time alerts with cleaner gating.' },
                        { id: 'post_analysis', label: 'Post Negotiation Analysis Only', desc: 'No live prompts. Post-call summary only.' }
                    ].map(opt => (
                        <button
                            key={opt.id}
                            onClick={() => setPreset(opt.id as 'practice' | 'live_call' | 'post_analysis')}
                            style={{
                                background: preset === opt.id ? 'rgba(0, 255, 65, 0.15)' : '#1c1c1c',
                                border: `1px solid ${preset === opt.id ? '#00ff41' : '#444'}`,
                                padding: '8px',
                                borderRadius: '6px',
                                cursor: 'pointer',
                                textAlign: 'left',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '2px'
                            }}
                        >
                            <div style={{ color: preset === opt.id ? '#00ff41' : '#eee', fontWeight: 'bold', fontSize: '13px' }}>
                                {opt.label}
                            </div>
                            <div style={{ color: '#888', fontSize: '10px' }}>
                                {opt.desc}
                            </div>
                        </button>
                    ))}
                </div>
            </div>

            <button
                onClick={handleStart}
                style={{
                    width: '100%',
                    background: '#00ff41',
                    color: '#000',
                    border: 'none',
                    padding: '10px',
                    borderRadius: '8px',
                    fontSize: '15px',
                    fontWeight: 'bold',
                    cursor: 'pointer',
                    marginTop: '4px',
                    marginBottom: '6px'
                }}
            >
                START SESSION
            </button>
            <div style={{ marginTop: '4px', fontSize: '9px', color: '#555' }}>
                You can pause or end at any time.
            </div>
        </div>
    );
}
