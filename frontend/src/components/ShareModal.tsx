import React, { useState } from 'react';
import { X, Copy, Check, Link as LinkIcon } from 'lucide-react';
import api from '../services/api';

interface ShareModalProps {
    docId: string;
    fileName: string;
    onClose: () => void;
}

const ShareModal: React.FC<ShareModalProps> = ({ docId, fileName, onClose }) => {
    const [passkey, setPasskey] = useState('');
    const [expiresAt, setExpiresAt] = useState('');
    const [generatedLink, setGeneratedLink] = useState<string | null>(null);
    const [isGenerating, setIsGenerating] = useState(false);
    const [isCopied, setIsCopied] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleGenerate = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsGenerating(true);
        setError(null);

        try {
            const payload: any = {};
            if (passkey.trim()) payload.passkey = passkey.trim();
            if (expiresAt) {
                // Convert minimal datetime-local to ISO if needed, or send as is if ISO-like
                const dateObj = new Date(expiresAt);
                payload.expires_at = dateObj.toISOString();
            }

            const response = await api.post(`/documents/${docId}/share`, payload);

            // Build the frontend URL
            const url = new URL(window.location.href);
            const shareUrl = `${url.protocol}//${url.host}/shared/${response.data.token}`;
            setGeneratedLink(shareUrl);
        } catch (err: any) {
            console.error('Share error:', err);
            setError(err.response?.data?.detail || 'Errore durante la generazione del link.');
        } finally {
            setIsGenerating(false);
        }
    };

    const handleCopy = () => {
        if (generatedLink) {
            navigator.clipboard.writeText(generatedLink);
            setIsCopied(true);
            setTimeout(() => setIsCopied(false), 2000);
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '400px' }}>
                <div className="modal-header">
                    <h2>Condividi Documento</h2>
                    <button className="close-btn" onClick={onClose}><X size={24} /></button>
                </div>

                {!generatedLink ? (
                    <form onSubmit={handleGenerate} className="modal-form">
                        <p style={{ marginBottom: '1rem', color: 'var(--text-muted)' }}>
                            Crea un link pubblico per <strong>{fileName}</strong>.
                        </p>

                        <div className="form-group">
                            <label htmlFor="passkey">Password di protezione (opzionale)</label>
                            <input
                                id="passkey"
                                type="password"
                                value={passkey}
                                onChange={e => setPasskey(e.target.value)}
                                placeholder="Lascia vuoto per renderlo pubblico"
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    borderRadius: '0.375rem',
                                    border: '1px solid var(--border)',
                                    backgroundColor: 'var(--bg-dark)',
                                    color: 'var(--text-light)',
                                    marginBottom: '1rem'
                                }}
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="expiresAt">Data di Scadenza (opzionale)</label>
                            <input
                                id="expiresAt"
                                type="datetime-local"
                                value={expiresAt}
                                onChange={e => setExpiresAt(e.target.value)}
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    borderRadius: '0.375rem',
                                    border: '1px solid var(--border)',
                                    backgroundColor: 'var(--bg-dark)',
                                    color: 'var(--text-light)'
                                }}
                            />
                        </div>

                        {error && <div className="error-message" style={{ color: 'var(--error)', marginTop: '0.5rem' }}>{error}</div>}

                        <div className="modal-actions" style={{ marginTop: '1.5rem' }}>
                            <button type="button" className="btn btn-secondary" onClick={onClose}>Annulla</button>
                            <button type="submit" className="btn btn-primary" disabled={isGenerating}>
                                {isGenerating ? 'Creazione...' : 'Genera Link'}
                            </button>
                        </div>
                    </form>
                ) : (
                    <div style={{ padding: '1rem 0' }}>
                        <div style={{ textAlign: 'center', marginBottom: '1.5rem', color: 'var(--accent)' }}>
                            <LinkIcon size={48} style={{ marginBottom: '1rem' }} />
                            <h3 style={{ margin: 0, color: 'var(--text-light)' }}>Link generato!</h3>
                        </div>

                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            backgroundColor: 'var(--bg-dark)',
                            padding: '0.5rem',
                            borderRadius: '0.375rem',
                            border: '1px solid var(--border)'
                        }}>
                            <input
                                type="text"
                                readOnly
                                value={generatedLink}
                                style={{
                                    flex: 1,
                                    background: 'transparent',
                                    border: 'none',
                                    color: 'var(--text-light)',
                                    fontSize: '0.9rem',
                                    outline: 'none',
                                    textOverflow: 'ellipsis'
                                }}
                            />
                            <button
                                onClick={handleCopy}
                                style={{
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    padding: '0.5rem',
                                    backgroundColor: 'var(--accent)',
                                    color: 'var(--bg-dark)',
                                    border: 'none',
                                    borderRadius: '0.25rem',
                                    cursor: 'pointer'
                                }}
                            >
                                {isCopied ? <Check size={18} /> : <Copy size={18} />}
                            </button>
                        </div>
                        <p style={{ marginTop: '1rem', fontSize: '0.85rem', color: 'var(--text-muted)', textAlign: 'center' }}>
                            Chiunque abbia questo link {passkey ? 'e la password ' : ''}potrà scaricare il documento.
                        </p>

                        <div className="modal-actions" style={{ marginTop: '1.5rem', justifyContent: 'center' }}>
                            <button className="btn btn-primary" onClick={onClose}>Chiudi</button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ShareModal;
