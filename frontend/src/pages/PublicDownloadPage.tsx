import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Download, AlertCircle, FileText, Lock } from 'lucide-react';
import api from '../services/api';

const PublicDownloadPage: React.FC = () => {
    const { token } = useParams<{ token: string }>();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [fileInfo, setFileInfo] = useState<{ filename: string; requires_passkey: boolean } | null>(null);
    const [passkey, setPasskey] = useState('');
    const [isDownloading, setIsDownloading] = useState(false);
    const [downloadProgress, setDownloadProgress] = useState<number | null>(null);

    useEffect(() => {
        const fetchInfo = async () => {
            try {
                const response = await api.get(`/shared/${token}`);
                setFileInfo(response.data);
            } catch (err: any) {
                console.error('Failed to fetch share info:', err);
                setError(err.response?.data?.detail || 'Link non valido o scaduto.');
            } finally {
                setLoading(false);
            }
        };
        fetchInfo();
    }, [token]);

    const handleDownload = async (e?: React.FormEvent) => {
        if (e) e.preventDefault();

        setIsDownloading(true);
        setError(null);
        setDownloadProgress(0);

        try {
            const response = await api.post(`/shared/${token}/download`,
                { passkey: passkey || null },
                {
                    responseType: 'blob',
                    onDownloadProgress: (progressEvent) => {
                        if (progressEvent.total) {
                            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                            setDownloadProgress(percent);
                        }
                    }
                }
            );

            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', fileInfo?.filename || 'documento');
            document.body.appendChild(link);
            link.click();
            link.parentNode?.removeChild(link);
            window.URL.revokeObjectURL(url);

            setDownloadProgress(null);
        } catch (err: any) {
            console.error('Download error:', err);
            setDownloadProgress(null);

            // If responseType is blob, we need to extract JSON from error blob to read detail
            if (err.response?.data instanceof Blob) {
                const text = await err.response.data.text();
                try {
                    const json = JSON.parse(text);
                    setError(json.detail || 'Accesso negato o file non trovato.');
                } catch {
                    setError('Errore durante il download.');
                }
            } else {
                setError(err.response?.data?.detail || 'Errore durante il download.');
            }
        } finally {
            setIsDownloading(false);
        }
    };

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', backgroundColor: 'var(--bg-dark)' }}>
                <div style={{ color: 'var(--accent)', fontSize: '1.2rem' }}>Caricamento in corso...</div>
            </div>
        );
    }

    if (error && !fileInfo) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', backgroundColor: 'var(--bg-dark)', padding: '2rem' }}>
                <div style={{
                    backgroundColor: 'var(--bg-card)', padding: '3rem', borderRadius: '1rem',
                    border: '1px solid var(--border)', textAlign: 'center', maxWidth: '500px'
                }}>
                    <AlertCircle size={64} style={{ color: 'var(--error)', margin: '0 auto 1.5rem auto' }} />
                    <h2 style={{ color: 'var(--text-light)', marginBottom: '1rem' }}>Ops! Qualcosa è andato storto</h2>
                    <p style={{ color: 'var(--text-muted)' }}>{error}</p>
                </div>
            </div>
        );
    }

    return (
        <div style={{
            display: 'flex', flexDirection: 'column', minHeight: '100vh',
            backgroundColor: 'var(--bg-dark)', alignItems: 'center', justifyContent: 'center', padding: '1rem'
        }}>
            <div style={{
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--glass)',
                borderRadius: '1rem',
                padding: '3rem',
                width: '100%',
                maxWidth: '500px',
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
                textAlign: 'center'
            }}>
                <FileText size={48} style={{ color: 'var(--accent)', margin: '0 auto 1.5rem auto' }} />

                <h2 style={{ color: 'var(--text-light)', marginBottom: '0.5rem', wordBreak: 'break-all' }}>
                    {fileInfo?.filename}
                </h2>
                <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>
                    Questo file è stato condiviso con te.
                </p>

                {fileInfo?.requires_passkey ? (
                    <form onSubmit={handleDownload}>
                        {error && <div style={{ color: 'var(--error)', marginBottom: '1rem', padding: '0.75rem', backgroundColor: 'rgba(239, 68, 68, 0.1)', borderRadius: '0.5rem', border: '1px solid var(--error)' }}>{error}</div>}

                        <div style={{ marginBottom: '1.5rem', textAlign: 'left' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)' }}>
                                <Lock size={14} style={{ display: 'inline', marginRight: '0.25rem', verticalAlign: 'middle' }} />
                                Inserisci la password per scaricare
                            </label>
                            <input
                                type="password"
                                value={passkey}
                                onChange={e => setPasskey(e.target.value)}
                                style={{
                                    width: '100%', padding: '0.75rem', borderRadius: '0.5rem',
                                    border: '1px solid var(--border)', backgroundColor: 'var(--bg-dark)',
                                    color: 'var(--text-light)', fontSize: '1rem'
                                }}
                                required
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={isDownloading || !passkey}
                            style={{
                                width: '100%', padding: '0.875rem', borderRadius: '0.5rem',
                                backgroundColor: isDownloading || !passkey ? 'var(--bg-dark)' : 'var(--accent)',
                                color: isDownloading || !passkey ? 'var(--text-muted)' : 'var(--bg-dark)',
                                border: isDownloading || !passkey ? '1px solid var(--border)' : 'none',
                                fontWeight: 600, fontSize: '1rem', cursor: isDownloading || !passkey ? 'not-allowed' : 'pointer',
                                transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem'
                            }}
                        >
                            <Download size={20} />
                            {isDownloading ? (downloadProgress ? `Download... ${downloadProgress}%` : 'Preparazione...') : 'Scarica Ora'}
                        </button>
                    </form>
                ) : (
                    <div>
                        {error && <div style={{ color: 'var(--error)', marginBottom: '1rem' }}>{error}</div>}
                        <button
                            onClick={() => handleDownload()}
                            disabled={isDownloading}
                            style={{
                                width: '100%', padding: '0.875rem', borderRadius: '0.5rem',
                                backgroundColor: isDownloading ? 'var(--bg-dark)' : 'var(--accent)',
                                color: isDownloading ? 'var(--text-muted)' : 'var(--bg-dark)',
                                border: isDownloading ? '1px solid var(--border)' : 'none',
                                fontWeight: 600, fontSize: '1rem', cursor: isDownloading ? 'not-allowed' : 'pointer',
                                transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem'
                            }}
                        >
                            <Download size={20} />
                            {isDownloading ? (downloadProgress ? `Download... ${downloadProgress}%` : 'Preparazione...') : 'Scarica Ora'}
                        </button>
                    </div>
                )}
            </div>
            <div style={{ marginTop: '2rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                Securely shared via <strong style={{ color: 'var(--accent)' }}>Documentale Local-First</strong>
            </div>
        </div>
    );
};

export default PublicDownloadPage;
