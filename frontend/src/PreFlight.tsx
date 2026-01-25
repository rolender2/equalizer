import { useState, useEffect } from 'react';

interface PreFlightProps {
    onStart: (config: { type: string }) => void;
}

export default function PreFlight({ onStart }: PreFlightProps) {
    const [types, setTypes] = useState<string[]>([]);
    const [selectedType, setSelectedType] = useState<string>('General');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('http://127.0.0.1:8000/negotiation-types')
            .then(res => res.json())
            .then(data => {
                setTypes(data.types);
                // Load saved preference
                const saved = localStorage.getItem('lastNegotiationType');
                if (saved && data.types.includes(saved)) {
                    setSelectedType(saved);
                } else if (data.default) {
                    setSelectedType(data.default);
                }
                setLoading(false);
            })
            .catch(err => {
                console.error('Failed to load types:', err);
                setTypes(['General']); // Fallback
                setLoading(false);
            });
    }, []);

    const handleStart = () => {
        localStorage.setItem('lastNegotiationType', selectedType);
        onStart({ type: selectedType });
    };

    if (loading) return <div style={{ color: '#00ff41' }}>Loading scenarios...</div>;

    return (
        <div style={{
            // @ts-ignore
            backgroundColor: 'rgba(0, 0, 0, 0.95)',
            border: '2px solid #00ff41',
            borderRadius: '16px',
            padding: '24px',
            color: '#fff',
            minWidth: '400px',
            textAlign: 'center',
            boxShadow: '0 8px 32px rgba(0, 255, 65, 0.2)',
            pointerEvents: 'auto'
        }}>
            <h2 style={{
                margin: '0 0 16px 0',
                fontSize: '18px',
                color: '#00ff41',
                // @ts-ignore
                WebkitAppRegion: 'drag',
                cursor: 'move',
                userSelect: 'none'
            }}>
                🚀 NEGOTIATION PRE-FLIGHT
            </h2>

            <div style={{ marginBottom: '20px', textAlign: 'left' }}>
                <label style={{ display: 'block', fontSize: '12px', color: '#888', marginBottom: '8px' }}>
                    SCENARIO TYPE
                </label>
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '8px'
                }}>
                    {types.map(type => (
                        <button
                            key={type}
                            onClick={() => setSelectedType(type)}
                            style={{
                                background: selectedType === type ? 'rgba(0, 255, 65, 0.2)' : '#222',
                                border: `1px solid ${selectedType === type ? '#00ff41' : '#444'}`,
                                color: selectedType === type ? '#00ff41' : '#aaa',
                                padding: '10px',
                                borderRadius: '6px',
                                cursor: 'pointer',
                                fontSize: '14px',
                                transition: 'all 0.2s'
                            }}
                        >
                            {type}
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
                    padding: '12px',
                    borderRadius: '8px',
                    fontSize: '16px',
                    fontWeight: 'bold',
                    cursor: 'pointer',
                    marginTop: '8px'
                }}
            >
                INITIALIZE SYSTEMS
            </button>
        </div>
    );
}
