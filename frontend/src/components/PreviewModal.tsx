import React, { useEffect, useState } from 'react';
import { X, AlertCircle } from 'lucide-react';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

interface Props {
    doc: { id: string; title: string; file_type?: string };
    onClose: () => void;
}

const PREVIEWABLE = [
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
];

const PreviewModal: React.FC<Props> = ({ doc, onClose }) => {
    const [blobUrl, setBlobUrl] = useState<string | null>(null);
    const [error, setError] = useState(false);
    const [loading, setLoading] = useState(true);
    const canPreview = !doc.file_type || PREVIEWABLE.includes(doc.file_type);

    useEffect(() => {
        if (!canPreview) {
            setLoading(false);
            return;
        }
        const token = localStorage.getItem('token');
        fetch(`${BASE_URL}/documents/${doc.id}/preview`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
            .then(async (res) => {
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const blob = await res.blob();
                setBlobUrl(URL.createObjectURL(blob));
            })
            .catch(() => setError(true))
            .finally(() => setLoading(false));

        return () => {
            if (blobUrl) URL.revokeObjectURL(blobUrl);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [doc.id]);

    const isImage = doc.file_type?.startsWith('image/');

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div
                className="modal preview-modal"
                onClick={(e) => e.stopPropagation()}
                style={{ width: '90vw', maxWidth: '1000px', height: '85vh', display: 'flex', flexDirection: 'column' }}
            >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <h2 style={{ margin: 0, fontSize: '1.1rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {doc.title}
                    </h2>
                    <button className="icon-btn" onClick={onClose} aria-label="Chiudi">
                        <X size={20} />
                    </button>
                </div>

                <div style={{ flex: 1, overflow: 'hidden', borderRadius: '0.5rem', background: 'rgba(0,0,0,0.3)' }}>
                    {loading && (
                        <div className="preview-placeholder">Caricamento anteprima…</div>
                    )}

                    {!loading && error && (
                        <div className="preview-placeholder">
                            <AlertCircle size={32} style={{ marginBottom: '0.5rem', color: 'var(--error)' }} />
                            <p>Impossibile caricare l'anteprima.</p>
                        </div>
                    )}

                    {!loading && !error && !canPreview && (
                        <div className="preview-placeholder">
                            <AlertCircle size={32} style={{ marginBottom: '0.5rem', color: 'var(--text-muted)' }} />
                            <p>Anteprima non disponibile per questo tipo di file.</p>
                            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Usa il tasto Scarica per aprire il documento.</p>
                        </div>
                    )}

                    {!loading && !error && canPreview && blobUrl && (
                        isImage ? (
                            <img
                                src={blobUrl}
                                alt={doc.title}
                                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                            />
                        ) : (
                            <iframe
                                src={blobUrl}
                                title={doc.title}
                                style={{ width: '100%', height: '100%', border: 'none' }}
                            />
                        )
                    )}
                </div>
            </div>
        </div>
    );
};

export default PreviewModal;
