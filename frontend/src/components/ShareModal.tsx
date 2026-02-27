import React, { useEffect, useState } from 'react';
import { X, Share2, Trash2, Loader } from 'lucide-react';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

interface Share {
    id: string;
    shared_with_id: string;
    created_at: string;
}

interface Props {
    doc: { id: string; title: string };
    onClose: () => void;
}

const ShareModal: React.FC<Props> = ({ doc, onClose }) => {
    const [email, setEmail] = useState('');
    const [shares, setShares] = useState<Share[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const token = localStorage.getItem('token');
    const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

    const fetchShares = async () => {
        try {
            const res = await fetch(`${BASE_URL}/documents/${doc.id}/shares`, { headers });
            if (res.ok) setShares(await res.json());
        } catch {
            // silenzioso
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchShares(); }, [doc.id]);

    const handleShare = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!email.trim()) return;
        setSaving(true);
        setError('');
        setSuccess('');
        try {
            const res = await fetch(`${BASE_URL}/documents/${doc.id}/share`, {
                method: 'POST',
                headers,
                body: JSON.stringify({ shared_with_email: email.trim() }),
            });
            const data = await res.json();
            if (!res.ok) {
                setError(data.detail || 'Errore durante la condivisione.');
            } else {
                setSuccess(`Documento condiviso con ${email.trim()}.`);
                setEmail('');
                await fetchShares();
            }
        } catch {
            setError('Errore di rete.');
        } finally {
            setSaving(false);
        }
    };

    const handleRevoke = async (shareId: string) => {
        try {
            await fetch(`${BASE_URL}/documents/${doc.id}/shares/${shareId}`, {
                method: 'DELETE',
                headers,
            });
            setShares((prev) => prev.filter((s) => s.id !== shareId));
        } catch {
            // silenzioso
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: '480px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Share2 size={18} /> Condividi
                    </h2>
                    <button className="icon-btn" onClick={onClose}><X size={20} /></button>
                </div>

                <p style={{ color: 'var(--text-muted)', marginBottom: '1rem', fontSize: '0.875rem' }}>
                    <strong>{doc.title}</strong>
                </p>

                <form onSubmit={handleShare}>
                    <label className="filter-label">Email utente</label>
                    <input
                        type="email"
                        className="input"
                        placeholder="utente@esempio.it"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                    />
                    {error && <p style={{ color: 'var(--error)', fontSize: '0.85rem', marginBottom: '0.5rem' }}>{error}</p>}
                    {success && <p style={{ color: '#22c55e', fontSize: '0.85rem', marginBottom: '0.5rem' }}>{success}</p>}
                    <button className="btn" type="submit" disabled={saving} style={{ width: 'auto', marginBottom: '1.5rem' }}>
                        {saving ? <Loader size={16} className="spin" /> : 'Condividi'}
                    </button>
                </form>

                <hr style={{ borderColor: 'var(--glass)', marginBottom: '1rem' }} />
                <p style={{ fontWeight: 600, marginBottom: '0.75rem', fontSize: '0.875rem' }}>Condivisioni attive</p>

                {loading ? (
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Caricamento…</p>
                ) : shares.length === 0 ? (
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Nessuna condivisione attiva.</p>
                ) : (
                    <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {shares.map((s) => (
                            <li key={s.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--glass)', borderRadius: '0.4rem', padding: '0.5rem 0.75rem' }}>
                                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                    ID: {s.shared_with_id.slice(0, 8)}… · {new Date(s.created_at).toLocaleDateString('it-IT')}
                                </span>
                                <button
                                    className="icon-btn"
                                    style={{ color: 'var(--error)' }}
                                    onClick={() => handleRevoke(s.id)}
                                    title="Revoca accesso"
                                >
                                    <Trash2 size={14} />
                                </button>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
};

export default ShareModal;
