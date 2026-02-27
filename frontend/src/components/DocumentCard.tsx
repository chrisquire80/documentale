import React, { useState, useCallback } from 'react';
import { FileDown, Calendar, User, Eye, Pencil, Trash2, Share2, Check, X, Loader } from 'lucide-react';
import api from '../services/api';
import PreviewModal from './PreviewModal';
import ShareModal from './ShareModal';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

interface Doc {
    id: string;
    title: string;
    file_type?: string;
    owner_id: string;
    is_restricted: boolean;
    created_at: string;
    doc_metadata?: { tags?: string[] };
}

interface Props {
    doc: Doc;
    onDeleted?: (id: string) => void;
    onUpdated?: (doc: Doc) => void;
}

const DocumentCard: React.FC<Props> = ({ doc, onDeleted, onUpdated }) => {
    // Download
    const [progress, setProgress] = useState<number | null>(null);
    const [downloadError, setDownloadError] = useState(false);

    // Modals
    const [showPreview, setShowPreview] = useState(false);
    const [showShare, setShowShare] = useState(false);

    // Inline edit
    const [editing, setEditing] = useState(false);
    const [editTitle, setEditTitle] = useState(doc.title);
    const [editRestricted, setEditRestricted] = useState(doc.is_restricted);
    const [saving, setSaving] = useState(false);

    // Delete
    const [deleting, setDeleting] = useState(false);

    // ── Download ──────────────────────────────────────────────────────────────
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
                if (total > 0) setProgress(Math.min(99, Math.round((received / total) * 100)));
            }
            setProgress(100);

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

            setTimeout(() => setProgress(null), 800);
        } catch {
            setDownloadError(true);
            setTimeout(() => { setDownloadError(false); setProgress(null); }, 2500);
        }
    }, [doc.id, doc.title]);

    // ── Inline edit ──────────────────────────────────────────────────────────
    const handleEditSave = async () => {
        if (!editTitle.trim()) return;
        setSaving(true);
        try {
            const res = await api.patch(`/documents/${doc.id}`, {
                title: editTitle.trim(),
                is_restricted: editRestricted,
            });
            onUpdated?.(res.data);
            setEditing(false);
        } catch {
            // silenzioso — mantieni la modalità edit
        } finally {
            setSaving(false);
        }
    };

    const handleEditCancel = () => {
        setEditTitle(doc.title);
        setEditRestricted(doc.is_restricted);
        setEditing(false);
    };

    // ── Soft delete ──────────────────────────────────────────────────────────
    const handleDelete = async () => {
        if (!window.confirm(`Spostare "${doc.title}" nel cestino?`)) return;
        setDeleting(true);
        try {
            await api.delete(`/documents/${doc.id}`);
            onDeleted?.(doc.id);
        } finally {
            setDeleting(false);
        }
    };

    return (
        <>
            <div className="doc-card">
                {/* ── Header ── */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem', gap: '0.5rem' }}>
                    {editing ? (
                        <input
                            className="input"
                            style={{ marginBottom: 0, fontSize: '1rem', flex: 1 }}
                            value={editTitle}
                            onChange={(e) => setEditTitle(e.target.value)}
                            autoFocus
                        />
                    ) : (
                        <h3 style={{ margin: 0, fontSize: '1.05rem', flex: 1, wordBreak: 'break-word' }}>{doc.title}</h3>
                    )}

                    {/* Azioni */}
                    <div style={{ display: 'flex', gap: '0.25rem', flexShrink: 0 }}>
                        {editing ? (
                            <>
                                <button className="icon-btn" style={{ color: '#22c55e' }} onClick={handleEditSave} disabled={saving} title="Salva">
                                    {saving ? <Loader size={16} className="spin" /> : <Check size={16} />}
                                </button>
                                <button className="icon-btn" style={{ color: 'var(--error)' }} onClick={handleEditCancel} title="Annulla">
                                    <X size={16} />
                                </button>
                            </>
                        ) : (
                            <>
                                <button className="icon-btn" onClick={() => setShowPreview(true)} title="Anteprima">
                                    <Eye size={16} />
                                </button>
                                <button className="icon-btn" onClick={() => setEditing(true)} title="Modifica">
                                    <Pencil size={16} />
                                </button>
                                <button className="icon-btn" onClick={() => setShowShare(true)} title="Condividi">
                                    <Share2 size={16} />
                                </button>
                                <button
                                    className="icon-btn"
                                    onClick={handleDownload}
                                    disabled={progress !== null}
                                    title={downloadError ? 'Download fallito' : 'Scarica'}
                                    style={{ color: downloadError ? 'var(--error)' : 'var(--accent)' }}
                                >
                                    <FileDown size={16} />
                                </button>
                                <button
                                    className="icon-btn"
                                    onClick={handleDelete}
                                    disabled={deleting}
                                    title="Elimina"
                                    style={{ color: 'var(--error)' }}
                                >
                                    {deleting ? <Loader size={16} className="spin" /> : <Trash2 size={16} />}
                                </button>
                            </>
                        )}
                    </div>
                </div>

                {/* Inline edit: campo is_restricted */}
                {editing && (
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', marginBottom: '0.75rem', cursor: 'pointer' }}>
                        <input
                            type="checkbox"
                            checked={editRestricted}
                            onChange={(e) => setEditRestricted(e.target.checked)}
                        />
                        Documento riservato
                    </label>
                )}

                {/* ── Meta ── */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                        <Calendar size={13} />
                        {new Date(doc.created_at).toLocaleDateString('it-IT')}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                        <User size={13} />
                        {String(doc.owner_id).slice(0, 8)}…
                    </div>
                    {doc.is_restricted && (
                        <span style={{ fontSize: '0.7rem', background: 'rgba(239,68,68,0.2)', color: '#fca5a5', padding: '0.15rem 0.4rem', borderRadius: '0.25rem', alignSelf: 'flex-start' }}>
                            Riservato
                        </span>
                    )}
                </div>

                {/* ── Tag ── */}
                {(doc.doc_metadata?.tags?.length ?? 0) > 0 && (
                    <div style={{ marginTop: '0.75rem', display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                        {doc.doc_metadata!.tags!.map((tag) => (
                            <span
                                key={tag}
                                style={{ background: 'var(--primary)', padding: '0.15rem 0.45rem', borderRadius: '0.25rem', fontSize: '0.72rem' }}
                            >
                                {tag}
                            </span>
                        ))}
                    </div>
                )}

                {/* ── Download progress ── */}
                {progress !== null && (
                    <div className="download-progress-bar">
                        <div
                            className={`download-progress-fill${downloadError ? ' download-progress-error' : ''}`}
                            style={{ width: downloadError ? '100%' : `${progress}%` }}
                        />
                    </div>
                )}
                {downloadError && (
                    <p style={{ margin: '0.25rem 0 0', fontSize: '0.72rem', color: 'var(--error)' }}>Download fallito. Riprova.</p>
                )}
            </div>

            {showPreview && <PreviewModal doc={doc} onClose={() => setShowPreview(false)} />}
            {showShare && <ShareModal doc={doc} onClose={() => setShowShare(false)} />}
        </>
    );
};

export default React.memo(DocumentCard);
