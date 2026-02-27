import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { X, RotateCcw, Trash2, Loader } from 'lucide-react';
import api from '../services/api';

interface Doc {
    id: string;
    title: string;
    file_type?: string;
    deleted_at?: string;
}

interface Props {
    onClose: () => void;
}

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

const TrashModal: React.FC<Props> = ({ onClose }) => {
    const queryClient = useQueryClient();
    const [pendingId, setPendingId] = useState<string | null>(null);

    const { data, isLoading, refetch } = useQuery<{ items: Doc[]; total: number }>({
        queryKey: ['trash'],
        queryFn: async () => {
            const res = await api.get('/documents/trash?limit=50&offset=0');
            return res.data;
        },
    });

    const token = localStorage.getItem('token');
    const authHeaders = { Authorization: `Bearer ${token}` };

    const handleRestore = async (id: string) => {
        setPendingId(id);
        try {
            await fetch(`${BASE_URL}/documents/${id}/restore`, { method: 'POST', headers: authHeaders });
            await refetch();
            queryClient.invalidateQueries({ queryKey: ['documents'] });
        } finally {
            setPendingId(null);
        }
    };

    const handlePermanentDelete = async (id: string, title: string) => {
        if (!window.confirm(`Eliminare definitivamente "${title}"? Operazione irreversibile.`)) return;
        setPendingId(id);
        try {
            await fetch(`${BASE_URL}/documents/${id}/permanent`, { method: 'DELETE', headers: authHeaders });
            await refetch();
        } finally {
            setPendingId(null);
        }
    };

    const docs = data?.items ?? [];

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: '600px', maxHeight: '80vh', display: 'flex', flexDirection: 'column' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Trash2 size={18} /> Cestino
                        {data && data.total > 0 && (
                            <span style={{ background: 'var(--error)', color: 'white', borderRadius: '999px', padding: '0 0.5rem', fontSize: '0.75rem' }}>
                                {data.total}
                            </span>
                        )}
                    </h2>
                    <button className="icon-btn" onClick={onClose}><X size={20} /></button>
                </div>

                <div style={{ overflowY: 'auto', flex: 1 }}>
                    {isLoading && <p style={{ color: 'var(--text-muted)' }}>Caricamento…</p>}
                    {!isLoading && docs.length === 0 && (
                        <p style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: '2rem' }}>
                            Il cestino è vuoto.
                        </p>
                    )}
                    {docs.map((doc) => (
                        <div key={doc.id} style={{
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                            background: 'var(--glass)', borderRadius: '0.5rem', padding: '0.75rem 1rem',
                            marginBottom: '0.5rem',
                        }}>
                            <div>
                                <p style={{ margin: 0, fontWeight: 600, fontSize: '0.9rem' }}>{doc.title}</p>
                                {doc.deleted_at && (
                                    <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                        Eliminato il {new Date(doc.deleted_at).toLocaleDateString('it-IT')}
                                    </p>
                                )}
                            </div>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <button
                                    className="icon-btn"
                                    style={{ color: '#22c55e' }}
                                    title="Ripristina"
                                    disabled={pendingId === doc.id}
                                    onClick={() => handleRestore(doc.id)}
                                >
                                    {pendingId === doc.id ? <Loader size={16} className="spin" /> : <RotateCcw size={16} />}
                                </button>
                                <button
                                    className="icon-btn"
                                    style={{ color: 'var(--error)' }}
                                    title="Elimina definitivamente"
                                    disabled={pendingId === doc.id}
                                    onClick={() => handlePermanentDelete(doc.id, doc.title)}
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default TrashModal;
