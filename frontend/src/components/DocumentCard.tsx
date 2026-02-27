import React, { useState, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { FileDown, Calendar, User as UserIcon, Eye, Pencil, Share2, MessageSquare, History, Trash2 } from 'lucide-react';
import DocumentPreviewModal from './DocumentPreviewModal';
import EditMetadataModal from './EditMetadataModal';
import DocumentVersionModal from './DocumentVersionModal';
import ShareModal from './ShareModal';
import CommentsPanel from './CommentsPanel';
import { useAuth } from '../store/AuthContext';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

const DocumentCard: React.FC<{
    doc: any;
    onUpdate?: () => void;
    isSelected?: boolean;
    onToggleSelect?: (id: string) => void;
}> = ({ doc, onUpdate, isSelected = false, onToggleSelect }) => {
    const { currentUser } = useAuth();
    const queryClient = useQueryClient();
    // null = idle | 0-100 = percentage during download
    const [progress, setProgress] = useState<number | null>(null);
    const [downloadError, setDownloadError] = useState(false);
    const [previewOpen, setPreviewOpen] = useState(false);
    const [editOpen, setEditOpen] = useState(false);
    const [shareOpen, setShareOpen] = useState(false);
    const [commentsOpen, setCommentsOpen] = useState(false);
    const [versionOpen, setVersionOpen] = useState(false);

    const canEdit = (currentUser?.role as string) === 'ADMIN' || currentUser?.id === doc.owner_id;

    const softDeleteMutation = useMutation({
        mutationFn: (docId: string) => {
            const token = localStorage.getItem('token');
            return axios.delete(`${BASE_URL}/api/documents/${docId}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
            if (onUpdate) onUpdate();
        }
    });

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
            const chunks: any[] = [];
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

    return (
        <div className="doc-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                <h3 style={{ margin: 0, fontSize: '1.125rem', paddingRight: '1rem', wordBreak: 'break-word' }}>{doc.title}</h3>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                    <button
                        onClick={() => setPreviewOpen(true)}
                        title="Anteprima in-browser"
                        style={{
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            color: 'var(--accent)',
                            display: 'flex',
                            alignItems: 'center',
                            padding: 0
                        }}
                    >
                        <Eye size={20} />
                    </button>
                    <button
                        onClick={() => setCommentsOpen(true)}
                        title="Commenti"
                        style={{
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            color: 'var(--text-light)',
                            display: 'flex',
                            alignItems: 'center',
                            padding: 0
                        }}
                    >
                        <MessageSquare size={18} />
                    </button>
                    <button
                        onClick={() => setShareOpen(true)}
                        title="Condividi Link"
                        style={{
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            color: 'var(--accent)',
                            display: 'flex',
                            alignItems: 'center',
                            padding: 0
                        }}
                    >
                        <Share2 size={18} />
                    </button>
                    {canEdit && (
                        <button
                            onClick={() => setEditOpen(true)}
                            title="Modifica Metadati"
                            style={{
                                background: 'none',
                                border: 'none',
                                cursor: 'pointer',
                                color: 'var(--text-muted)',
                                display: 'flex',
                                alignItems: 'center',
                                padding: 0
                            }}
                        >
                            <Pencil size={18} />
                        </button>
                    )}
                    <button
                        onClick={() => setVersionOpen(true)}
                        title="Storico Versioni"
                        style={{
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            color: 'var(--text-muted)',
                            display: 'flex',
                            alignItems: 'center',
                            padding: 0
                        }}
                    >
                        <History size={18} />
                    </button>
                    {canEdit && (
                        <button
                            onClick={() => {
                                if (confirm('Sei sicuro di voler spostare questo documento nel cestino?')) {
                                    softDeleteMutation.mutate(doc.id);
                                }
                            }}
                            disabled={softDeleteMutation.isPending}
                            title="Sposta nel Cestino"
                            style={{
                                background: 'none',
                                border: 'none',
                                cursor: softDeleteMutation.isPending ? 'wait' : 'pointer',
                                color: 'var(--error)',
                                display: 'flex',
                                alignItems: 'center',
                                padding: 0,
                                opacity: softDeleteMutation.isPending ? 0.5 : 1
                            }}
                        >
                            <Trash2 size={18} />
                        </button>
                    )}
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
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                    <Calendar size={14} />
                    {new Date(doc.created_at).toLocaleDateString('it-IT')}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                    <UserIcon size={14} />
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

            {/* Checkbox di selezione bulk (floating on top-left) */}
            {onToggleSelect && (
                <div
                    onClick={(e) => { e.stopPropagation(); onToggleSelect(doc.id); }}
                    style={{
                        position: 'absolute',
                        top: '1rem',
                        left: '-1rem',
                        width: '28px',
                        height: '28px',
                        borderRadius: '6px',
                        backgroundColor: isSelected ? 'var(--accent)' : 'rgba(0,0,0,0.4)',
                        border: `2px solid ${isSelected ? 'var(--accent)' : 'var(--glass)'}`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer',
                        opacity: isSelected ? 1 : 0,
                        transition: 'opacity 0.2s, background-color 0.2s',
                        zIndex: 10,
                        boxShadow: '0 2px 10px rgba(0,0,0,0.3)',
                    }}
                    className="doc-checkbox"
                >
                    {isSelected && (
                        <svg viewBox="0 0 24 24" fill="none" stroke="var(--bg-dark)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" style={{ width: '16px', height: '16px' }}>
                            <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                    )}
                </div>
            )}

            {previewOpen && (
                <DocumentPreviewModal
                    isOpen={previewOpen}
                    onClose={() => setPreviewOpen(false)}
                    doc={doc}
                />
            )}

            {editOpen && (
                <EditMetadataModal
                    isOpen={editOpen}
                    onClose={() => setEditOpen(false)}
                    doc={doc}
                    onSaveSuccess={() => {
                        if (onUpdate) onUpdate();
                    }}
                />
            )}

            {shareOpen && (
                <ShareModal
                    docId={doc.id}
                    fileName={doc.title}
                    onClose={() => setShareOpen(false)}
                />
            )}

            {commentsOpen && (
                <CommentsPanel
                    docId={doc.id}
                    docTitle={doc.title}
                    onClose={() => setCommentsOpen(false)}
                />
            )}

            {versionOpen && (
                <DocumentVersionModal
                    isOpen={versionOpen}
                    onClose={() => setVersionOpen(false)}
                    doc={doc}
                />
            )}
        </div>
    );
};

export default React.memo(DocumentCard);
