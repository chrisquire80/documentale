import React, { useState, useEffect } from 'react';
import { X, Loader2, GitCompareArrows } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

interface CompareModalProps {
    isOpen: boolean;
    onClose: () => void;
    documentIds: string[];
}

const CompareModal: React.FC<CompareModalProps> = ({ isOpen, onClose, documentIds }) => {
    const [loading, setLoading] = useState(false);
    const [comparison, setComparison] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!isOpen || documentIds.length < 2) return;

        const fetchComparison = async () => {
            setLoading(true);
            setError(null);
            setComparison(null);

            try {
                const token = localStorage.getItem('token');
                const res = await fetch(`${BASE_URL}/ai/compare`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify({ doc_ids: documentIds }),
                });

                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    throw new Error(data.detail || `Errore ${res.status}`);
                }

                const data = await res.json();
                setComparison(data.comparison);
            } catch (err: any) {
                setError(err.message || 'Errore durante il confronto.');
            } finally {
                setLoading(false);
            }
        };

        fetchComparison();
    }, [isOpen, documentIds]);

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose} style={{ zIndex: 1100 }}>
            <div
                className="modal-content compare-modal"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="compare-modal-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                        <GitCompareArrows size={22} color="var(--accent)" />
                        <h2 style={{ margin: 0, fontSize: '1.15rem' }}>
                            Confronto AI — {documentIds.length} documenti
                        </h2>
                    </div>
                    <button
                        onClick={onClose}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-main)' }}
                    >
                        <X size={22} />
                    </button>
                </div>

                {/* Body */}
                <div className="compare-modal-body">
                    {loading && (
                        <div className="compare-loading">
                            <Loader2 size={28} style={{ animation: 'spin 1s linear infinite' }} />
                            <p>Gemini sta analizzando i documenti selezionati…</p>
                            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                                L'analisi potrebbe richiedere alcuni secondi.
                            </span>
                        </div>
                    )}

                    {error && (
                        <div style={{
                            padding: '1rem',
                            backgroundColor: 'rgba(239, 68, 68, 0.1)',
                            borderLeft: '4px solid var(--error)',
                            color: 'var(--error)',
                            borderRadius: '0.5rem',
                        }}>
                            ⚠️ {error}
                        </div>
                    )}

                    {comparison && (
                        <div className="compare-result">
                            <ReactMarkdown>{comparison}</ReactMarkdown>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default CompareModal;
