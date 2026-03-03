import React, { useState, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { FileDown, Calendar, User as UserIcon, Eye, Pencil, Share2, MessageSquare, History, Trash2, Upload as UploadIcon, Link2, Bot } from 'lucide-react';
import DocumentPreviewModal from './DocumentPreviewModal';
import EditMetadataModal from './EditMetadataModal';
import DocumentVersionModal from './DocumentVersionModal';
import ShareModal from './ShareModal';
import CommentsPanel from './CommentsPanel';
import UploadModal from './UploadModal';
import RelatedDocumentsModal from './RelatedDocumentsModal';
import { useAuth } from '../store/AuthContext';

/** Badge indicatore di indicizzazione AI (riutilizzato anche in DocumentRow) */
export const IndexBadge: React.FC<{ isIndexed: boolean }> = ({ isIndexed }) => (
    <span
        className={`index-badge ${isIndexed ? 'indexed' : 'not-indexed'}`}
        title={isIndexed ? 'Indicizzato dall\'AI — pronto per la chat RAG' : 'In attesa di elaborazione AI'}
    >
        <span className="index-badge-dot" />
        {isIndexed ? 'AI pronto' : 'In elaborazione'}
    </span>
);

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

const DocumentCard: React.FC<{
    doc: any;
    onUpdate?: () => void;
    isSelected?: boolean;
    onToggleSelect?: (id: string) => void;
    onChatOpen?: (doc: any) => void;
    onPreview?: (doc: any) => void;
}> = ({ doc, onUpdate, isSelected = false, onToggleSelect, onChatOpen, onPreview }) => {
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
    const [uploadVersionOpen, setUploadVersionOpen] = useState(false);
    const [relatedOpen, setRelatedOpen] = useState(false);

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
        <div
            className="doc-card"
            draggable
            onDragStart={(e) => {
                e.dataTransfer.setData('application/x-doc-id', doc.id);
                e.dataTransfer.setData('application/x-doc-title', doc.title);
                e.dataTransfer.effectAllowed = 'copy';
            }}
        >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem', gap: '1rem' }}>
                <h3 style={{
                    margin: 0,
                    fontSize: '1.125rem',
                    fontWeight: 700,
                    lineHeight: '1.4',
                    flex: 1,
                    minWidth: '150px',
                    wordBreak: 'break-word',
                    color: 'var(--text-main)'
                }}>
                    {doc.title}
                </h3>
                {doc.doc_metadata?.summary && (
                    <div className="hover-preview-tooltip">{doc.doc_metadata.summary}</div>
                )}
                <div style={{ display: 'flex', gap: '0.4rem', flexShrink: 0 }}>
                    <button
                        onClick={() => onPreview ? onPreview(doc) : setPreviewOpen(true)}
                        title="Anteprima"
                        className="icon-btn"
                        style={{ color: 'var(--accent)', padding: '0.4rem' }}
                    >
                        <Eye size={20} />
                    </button>
                    <button
                        onClick={handleDownload}
                        disabled={progress !== null}
                        title="Scarica"
                        className="icon-btn"
                        style={{ color: downloadError ? 'var(--error)' : 'var(--accent)', padding: '0.4rem' }}
                    >
                        <FileDown size={20} />
                    </button>
                    {onToggleSelect && (
                        <div
                            onClick={(e) => { e.stopPropagation(); onToggleSelect(doc.id); }}
                            className={`doc-checkbox-inline ${isSelected ? 'selected' : ''}`}
                            title="Seleziona"
                            style={{ flexShrink: 0 }}
                        >
                            {isSelected && (
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="4">
                                    <polyline points="20 6 9 17 4 12"></polyline>
                                </svg>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Azioni Secondarie - Row dedicata */}
            <div style={{
                display: 'flex',
                gap: '0.4rem',
                marginBottom: '1rem',
                padding: '0.5rem',
                background: 'rgba(0,0,0,0.25)',
                borderRadius: '0.6rem',
                flexWrap: 'wrap',
                border: '1px solid var(--glass)'
            }}>
                <button onClick={() => onChatOpen?.(doc)} title="Chiedi all'AI" className="icon-btn" style={{ color: '#2563eb' }}>
                    <Bot size={16} />
                </button>
                <div style={{ width: '1px', height: '16px', background: 'var(--glass)', margin: '0 0.1rem', alignSelf: 'center' }} />
                <button onClick={() => setCommentsOpen(true)} title="Commenti" className="icon-btn">
                    <MessageSquare size={16} />
                </button>
                <button onClick={() => setShareOpen(true)} title="Condividi" className="icon-btn">
                    <Share2 size={16} />
                </button>
                <button onClick={() => setVersionOpen(true)} title="Versioni" className="icon-btn">
                    <History size={16} />
                </button>
                <button onClick={() => setRelatedOpen(true)} title="Correlati" className="icon-btn">
                    <Link2 size={16} />
                </button>
                {canEdit && (
                    <>
                        <div style={{ width: '1px', height: '16px', background: 'var(--glass)', margin: '0 0.2rem', alignSelf: 'center' }} />
                        <button onClick={() => setEditOpen(true)} title="Modifica" className="icon-btn">
                            <Pencil size={16} />
                        </button>
                        <button onClick={() => setUploadVersionOpen(true)} title="Nuova Versione" className="icon-btn">
                            <UploadIcon size={16} />
                        </button>
                        <button
                            onClick={() => {
                                if (confirm('Spostare nel cestino?')) softDeleteMutation.mutate(doc.id);
                            }}
                            className="icon-btn"
                            style={{ color: 'var(--error)' }}
                            title="Cestino"
                        >
                            <Trash2 size={16} />
                        </button>
                    </>
                )}
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

            {doc.highlight_snippet && (
                <div
                    className="doc-card-snippet"
                    dangerouslySetInnerHTML={{ __html: doc.highlight_snippet }}
                />
            )}

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

            {uploadVersionOpen && (
                <UploadModal
                    onClose={() => setUploadVersionOpen(false)}
                    onSuccess={() => {
                        setUploadVersionOpen(false);
                        if (onUpdate) onUpdate();
                    }}
                    targetDocId={doc.id}
                />
            )}

            {relatedOpen && (
                <RelatedDocumentsModal
                    isOpen={relatedOpen}
                    onClose={() => setRelatedOpen(false)}
                    docId={doc.id}
                    docTitle={doc.title}
                />
            )}
        </div>
    );
};

export default React.memo(DocumentCard);
