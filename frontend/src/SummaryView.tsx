import React from 'react';

interface SummaryViewProps {
    summary: {
        strong_move?: string;
        missed_opportunity?: string;
        improvement_tip?: string;
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
                <h2 style={{ color: '#ff4444', margin: '0 0 16px 0' }}>
                    ⚠️ Summary Error
                </h2>
                <p>{summary.error}</p>
                <button
                    onClick={onClose}
                    style={{
                        marginTop: '16px',
                        background: '#333',
                        color: '#fff',
                        border: '1px solid #666',
                        borderRadius: '6px',
                        padding: '8px 16px',
                        cursor: 'pointer'
                    }}
                >
                    Close
                </button>
            </div>
        );
    }

    return (
        <div style={{
            background: 'rgba(0, 0, 0, 0.95)',
            border: '2px solid #00ff00',
            borderRadius: '12px',
            padding: '24px',
            minWidth: '350px',
            maxWidth: '500px',
            color: '#fff',
            fontFamily: 'monospace',
            // @ts-ignore
            WebkitAppRegion: 'no-drag',
            pointerEvents: 'auto'
        }}>
            <h2 style={{ color: '#00ff00', margin: '0 0 20px 0', fontSize: '18px' }}>
                📊 Session Reflection
            </h2>

            {/* Strong Move */}
            <div style={{ marginBottom: '16px' }}>
                <div style={{
                    color: '#4CAF50',
                    fontWeight: 'bold',
                    marginBottom: '4px',
                    fontSize: '14px'
                }}>
                    ✅ Strong Move
                </div>
                <div style={{
                    fontSize: '13px',
                    lineHeight: '1.4',
                    paddingLeft: '20px',
                    borderLeft: '3px solid #4CAF50'
                }}>
                    {summary.strong_move || 'No data'}
                </div>
            </div>

            {/* Missed Opportunity */}
            <div style={{ marginBottom: '16px' }}>
                <div style={{
                    color: '#ff9800',
                    fontWeight: 'bold',
                    marginBottom: '4px',
                    fontSize: '14px'
                }}>
                    ⚠️ Missed Opportunity
                </div>
                <div style={{
                    fontSize: '13px',
                    lineHeight: '1.4',
                    paddingLeft: '20px',
                    borderLeft: '3px solid #ff9800'
                }}>
                    {summary.missed_opportunity || 'No data'}
                </div>
            </div>

            {/* Improvement Tip */}
            <div style={{ marginBottom: '20px' }}>
                <div style={{
                    color: '#2196F3',
                    fontWeight: 'bold',
                    marginBottom: '4px',
                    fontSize: '14px'
                }}>
                    💡 Tip for Next Time
                </div>
                <div style={{
                    fontSize: '13px',
                    lineHeight: '1.4',
                    paddingLeft: '20px',
                    borderLeft: '3px solid #2196F3'
                }}>
                    {summary.improvement_tip || 'No data'}
                </div>
            </div>

            <button
                onClick={onClose}
                style={{
                    // @ts-ignore
                    WebkitAppRegion: 'no-drag',
                    width: '100%',
                    background: '#00ff00',
                    color: '#000',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '10px 16px',
                    cursor: 'pointer',
                    fontWeight: 'bold',
                    fontSize: '14px'
                }}
            >
                Done
            </button>
        </div>
    );
};

export default SummaryView;
