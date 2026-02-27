import React, { useEffect, useState } from 'react';
import { X, Clock, FileDown, History } from 'lucide-react';

interface DocumentVersion {
    version_num: number;
    created_at: string;
}

interface DocumentVersionModalProps {
    isOpen: boolean;
    onClose: () => void;
    doc: any;
}

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

const DocumentVersionModal: React.FC<DocumentVersionModalProps> = ({ isOpen, onClose, doc }) => {
    const [versions, setVersions] = useState<DocumentVersion[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen && doc) {
            fetchVersions();
        }
    }, [isOpen, doc]);

    const fetchVersions = async () => {
        setLoading(true);
        setError(null);
        try {
            const token = localStorage.getItem('token');
            const resp = await fetch(`${BASE_URL}/documents/${doc.id}/versions`, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            });
            if (!resp.ok) throw new Error('Fallito caricamento versioni');
            const data = await resp.json();
            setVersions(data);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadVersion = async (verNum: number) => {
        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`${BASE_URL}/documents/${doc.id}/download?version=${verNum}`, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const disposition = response.headers.get('Content-Disposition') ?? '';
            const match = disposition.match(/filename="(.+?)"/);
            const filename = match ? match[1] : `${doc.title}_v${verNum}`;

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Download versione fallito', err);
            alert('Errore durante il download della versione.');
        }
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose} style={{ zIndex: 1000 }}>
            <div
                className="modal-content"
                onClick={e => e.stopPropagation()}
                style={{
                    width: '100%',
                    maxWidth: '500px',
                    backgroundColor: 'var(--bg-dark)',
                    border: '1px solid var(--glass)',
                    boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
                    padding: '1.5rem',
                }}
            >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <div style={{ background: 'var(--primary-light)', padding: '0.5rem', borderRadius: '10px' }}>
                            <History size={20} color="var(--accent)" />
                        </div>
                        <h2 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--text)' }}>Cronologia Versioni</h2>
                    </div>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                        <X size={24} />
                    </button>
                </div>

                <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
                    Visualizza e scarica le versioni precedenti di <strong>{doc.title}</strong>.
                </p>

                {loading ? (
                    <div style={{ textAlign: 'center', padding: '2rem' }}>
                        <div className="spinner" style={{ margin: '0 auto' }}></div>
                        <p style={{ marginTop: '1rem', color: 'var(--text-muted)' }}>Caricamento...</p>
                    </div>
                ) : error ? (
                    <div style={{ color: 'var(--error)', padding: '1rem', textAlign: 'center' }}>
                        {error}
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '400px', overflowY: 'auto', paddingRight: '0.5rem' }}>
                        {versions.map((v) => (
                            <div
                                key={v.version_num}
                                style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    padding: '1rem',
                                    backgroundColor: 'rgba(255,255,255,0.03)',
                                    borderRadius: '12px',
                                    border: v.version_num === doc.current_version ? '1px solid var(--accent)' : '1px solid transparent',
                                }}
                            >
                                <div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                        <span style={{ fontWeight: 600, color: 'var(--text)' }}>Versione {v.version_num}</span>
                                        {v.version_num === doc.current_version && (
                                            <span style={{ fontSize: '0.7rem', backgroundColor: 'var(--accent)', color: 'var(--bg-dark)', padding: '0.1rem 0.4rem', borderRadius: '4px', fontWeight: 700 }}>ATTUALE</span>
                                        )}
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '0.25rem' }}>
                                        <Clock size={12} />
                                        {new Date(v.created_at).toLocaleString('it-IT')}
                                    </div>
                                </div>
                                <button
                                    onClick={() => handleDownloadVersion(v.version_num)}
                                    className="btn-icon"
                                    title="Scarica questa versione"
                                    style={{
                                        backgroundColor: 'rgba(255,255,255,0.05)',
                                        color: 'var(--accent)',
                                        width: '36px',
                                        height: '36px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        borderRadius: '8px',
                                        cursor: 'pointer',
                                        border: 'none',
                                    }}
                                >
                                    <FileDown size={18} />
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default DocumentVersionModal;
