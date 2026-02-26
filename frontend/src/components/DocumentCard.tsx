import React, { useState, useCallback } from 'react';
import { FileDown, Calendar, User } from 'lucide-react';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

const DocumentCard: React.FC<{ doc: any }> = ({ doc }) => {
    // null = idle | 0-100 = percentage during download
    const [progress, setProgress] = useState<number | null>(null);
    const [downloadError, setDownloadError] = useState(false);

    const handleDownload = useCallback(async () => {
        setProgress(0);
        setDownloadError(false);

        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`${BASE_URL}/documents/${doc.id}/download`, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const contentLength = response.headers.get('Content-Length');
            const total = contentLength ? parseInt(contentLength, 10) : 0;

            const reader = response.body!.getReader();
            const chunks: Uint8Array[] = [];
            let received = 0;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                chunks.push(value);
                received += value.length;
                if (total > 0) {
                    setProgress(Math.min(99, Math.round((received / total) * 100)));
                }
            }

            setProgress(100);

            // Use filename from Content-Disposition if available
            const disposition = response.headers.get('Content-Disposition') ?? '';
            const match = disposition.match(/filename="(.+?)"/);
            const filename = match ? match[1] : doc.title;

            const blob = new Blob(chunks);
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(url);

            // Brief pause so the user sees 100% before the bar disappears
            setTimeout(() => setProgress(null), 800);
        } catch (err) {
            console.error('Download failed', err);
            setDownloadError(true);
            setTimeout(() => {
                setDownloadError(false);
                setProgress(null);
            }, 2500);
        }
    }, [doc.id, doc.title]);

    return (
        <div className="doc-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                <h3 style={{ margin: 0, fontSize: '1.125rem' }}>{doc.title}</h3>
                <button
                    onClick={handleDownload}
                    disabled={progress !== null}
                    title={downloadError ? 'Download fallito' : 'Scarica'}
                    style={{
                        background: 'none',
                        border: 'none',
                        cursor: progress !== null ? 'not-allowed' : 'pointer',
                        color: downloadError ? 'var(--error)' : 'var(--accent)',
                        opacity: progress !== null && !downloadError ? 0.55 : 1,
                        display: 'flex',
                        alignItems: 'center',
                    }}
                >
                    <FileDown size={20} />
                </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                    <Calendar size={14} />
                    {new Date(doc.created_at).toLocaleDateString('it-IT')}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                    <User size={14} />
                    {String(doc.owner_id).slice(0, 8)}…
                </div>
            </div>

            <div style={{ marginTop: '1rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {doc.doc_metadata?.tags?.map((tag: string) => (
                    <span
                        key={tag}
                        style={{ background: 'var(--primary)', padding: '0.2rem 0.5rem', borderRadius: '0.25rem', fontSize: '0.75rem' }}
                    >
                        {tag}
                    </span>
                ))}
            </div>

            {/* Streaming download progress bar */}
            {progress !== null && (
                <div className="download-progress-bar">
                    <div
                        className={`download-progress-fill${downloadError ? ' download-progress-error' : ''}`}
                        style={{ width: downloadError ? '100%' : `${progress}%` }}
                    />
                </div>
            )}
            {downloadError && (
                <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', color: 'var(--error)' }}>
                    Download fallito. Riprova.
                </p>
            )}
        </div>
    );
};

export default React.memo(DocumentCard);
