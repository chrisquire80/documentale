import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { X, AlertTriangle, CheckCircle, ArrowRight, ShieldAlert, Info } from 'lucide-react';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

interface Conflict {
    id: string;
    field: string;
    old_value: string;
    new_value: string;
    severity: string;
    explanation: string;
    status: string;
    reference_doc_id?: string;
}

interface ConflictResolutionModalProps {
    isOpen: boolean;
    onClose: () => void;
    doc: any;
}

const ConflictResolutionModal: React.FC<ConflictResolutionModalProps> = ({ isOpen, onClose, doc }) => {
    const queryClient = useQueryClient();
    const [resolvingId, setResolvingId] = useState<string | null>(null);

    const resolveMutation = useMutation({
        mutationFn: ({ conflictId, action }: { conflictId: string, action: 'resolve' | 'ignore' }) => {
            const token = localStorage.getItem('token');
            return axios.post(`${BASE_URL}/documents/${doc.id}/conflicts/${conflictId}/resolve`, {}, {
                params: { action },
                headers: { Authorization: `Bearer ${token}` }
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
        }
    });

    if (!isOpen) return null;

    const pendingConflicts = doc.conflicts?.filter((c: any) => c.status === 'pending') || [];

    return (
        <div className="modal-overlay">
            <div className="modal preview-modal" style={{ maxWidth: '800px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <div style={{ background: 'rgba(239, 68, 68, 0.1)', padding: '0.5rem', borderRadius: '0.5rem' }}>
                            <ShieldAlert color="#ef4444" size={24} />
                        </div>
                        <div>
                            <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Smart Comparison & Resoluzione</h2>
                            <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                                Rilevate {pendingConflicts.length} discrepanze critiche con altri documenti.
                            </p>
                        </div>
                    </div>
                    <button onClick={onClose} className="icon-btn"><X size={20} /></button>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {pendingConflicts.map((conflict: Conflict) => (
                        <div key={conflict.id} style={{
                            background: 'rgba(0,0,0,0.2)',
                            border: '1px solid var(--glass)',
                            borderRadius: '0.75rem',
                            padding: '1.25rem',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '1rem'
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <span style={{
                                        fontSize: '0.7rem',
                                        background: conflict.severity === 'High' ? '#ef4444' : '#f59e0b',
                                        color: '#fff',
                                        padding: '2px 8px',
                                        borderRadius: '4px',
                                        fontWeight: 'bold',
                                        textTransform: 'uppercase'
                                    }}>
                                        {conflict.severity} Priority
                                    </span>
                                    <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>{conflict.field}</span>
                                </div>
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '1rem', alignItems: 'center' }}>
                                <div style={{ background: 'var(--bg-dark)', padding: '1rem', borderRadius: '0.5rem', border: '1px solid var(--glass)' }}>
                                    <label style={{ fontSize: '0.65rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>RIFERIMENTO</label>
                                    <div style={{ fontWeight: 500 }}>{conflict.old_value || 'N/A'}</div>
                                </div>
                                <ArrowRight size={20} color="var(--text-muted)" />
                                <div style={{ background: 'rgba(56, 189, 248, 0.05)', padding: '1rem', borderRadius: '0.5rem', border: '1px solid #38bdf844' }}>
                                    <label style={{ fontSize: '0.65rem', color: '#38bdf8', display: 'block', marginBottom: '0.25rem' }}>QUESTO DOCUMENTO</label>
                                    <div style={{ fontWeight: 500, color: '#38bdf8' }}>{conflict.new_value || 'N/A'}</div>
                                </div>
                            </div>

                            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', background: 'rgba(255,255,255,0.03)', padding: '0.75rem', borderRadius: '0.5rem' }}>
                                <Info size={16} color="var(--text-muted)" style={{ flexShrink: 0, marginTop: '2px' }} />
                                <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                                    {conflict.explanation}
                                </p>
                            </div>

                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
                                <button
                                    onClick={() => resolveMutation.mutate({ conflictId: conflict.id, action: 'ignore' })}
                                    className="btn"
                                    style={{ width: 'auto', background: 'transparent', border: '1px solid var(--glass)', fontSize: '0.875rem' }}
                                >
                                    Ignora
                                </button>
                                <button
                                    onClick={() => resolveMutation.mutate({ conflictId: conflict.id, action: 'resolve' })}
                                    className="btn"
                                    style={{ width: 'auto', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                                >
                                    <CheckCircle size={16} /> Approva Valore Attuale
                                </button>
                            </div>
                        </div>
                    ))}

                    {pendingConflicts.length === 0 && (
                        <div style={{ textAlign: 'center', padding: '3rem 0' }}>
                            <CheckCircle size={48} color="#10b981" style={{ marginBottom: '1rem', opacity: 0.5 }} />
                            <h3>Tutti i conflitti sono stati risolti</h3>
                            <p style={{ color: 'var(--text-muted)' }}>Non ci sono ulteriori discrepanze semantiche rilevate dall'AI.</p>
                            <button onClick={onClose} className="btn" style={{ width: 'auto', marginTop: '1rem' }}>Chiudi</button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ConflictResolutionModal;
