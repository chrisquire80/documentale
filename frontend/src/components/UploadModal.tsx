import React, { useState } from 'react';
import { X } from 'lucide-react';
import api from '../services/api';

const UploadModal: React.FC<{ onClose: () => void, onSuccess: () => void, targetDocId?: string }> = ({ onClose, onSuccess, targetDocId }) => {
    const [file, setFile] = useState<File | null>(null);
    const [title, setTitle] = useState('');
    const [isRestricted, setIsRestricted] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!file) return;

        setIsUploading(true);
        setError(null);
        const formData = new FormData();
        formData.append('file', file);
        if (!targetDocId) {
            formData.append('title', title || file.name);
            formData.append('is_restricted', isRestricted.toString());
            formData.append('metadata_json', JSON.stringify({ tags: ['auto-upload'] }));
        }

        try {
            if (targetDocId) {
                await api.post(`/documents/${targetDocId}/versions`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
            } else {
                await api.post('/documents/upload', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
            }
            onSuccess();
        } catch (err: any) {
            console.error('Upload failed', err);
            setError(err.response?.data?.detail || 'Errore durante il caricamento del file. Verifica il formato e riprova.');
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
            <div className="auth-card" style={{ margin: 0, position: 'relative' }}>
                <button onClick={onClose} style={{ position: 'absolute', right: '1rem', top: '1rem', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                    <X />
                </button>
                <h2 style={{ marginBottom: '1.5rem' }}>{targetDocId ? 'Carica Nuova Versione' : 'Carica Documento'}</h2>
                <form onSubmit={handleSubmit}>
                    {!targetDocId && (
                        <div style={{ marginBottom: '1rem' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Titolo (Opzionale)</label>
                            <input className="input" placeholder="Titolo" value={title} onChange={e => setTitle(e.target.value)} />
                        </div>
                    )}

                    <div style={{ marginBottom: '1rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>File (PDF, Doc, Txt, Immagini)</label>
                        <input
                            type="file"
                            className="input"
                            accept=".pdf,.doc,.docx,.txt,image/*"
                            style={{ border: '1px dashed var(--glass)', padding: '2rem', height: 'auto' }}
                            onChange={e => {
                                setFile(e.target.files?.[0] || null);
                                setError(null);
                            }}
                            required
                        />
                    </div>

                    {!targetDocId && (
                        <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <input type="checkbox" checked={isRestricted} onChange={e => setIsRestricted(e.target.checked)} id="restricted" />
                            <label htmlFor="restricted" style={{ fontSize: '0.875rem' }}>Documento Riservato</label>
                        </div>
                    )}

                    {error && (
                        <div style={{ marginBottom: '1rem', padding: '0.75rem', backgroundColor: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', borderRadius: '0.375rem', fontSize: '0.875rem' }}>
                            {error}
                        </div>
                    )}

                    <button className="btn" type="submit" disabled={isUploading || !file}>
                        {isUploading ? 'Caricamento...' : 'Carica'}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default UploadModal;
