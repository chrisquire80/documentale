import React, { useState, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { FileDown, Calendar, Eye, Pencil, Share2, Bot, Trash2, MessageSquare } from 'lucide-react';
import DocumentPreviewModal from './DocumentPreviewModal';
import EditMetadataModal from './EditMetadataModal';
import ShareModal from './ShareModal';
import CommentsPanel from './CommentsPanel';
import { IndexBadge } from './DocumentCard';
import { useAuth } from '../store/AuthContext';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

const DocumentRow: React.FC<{
    doc: any;
    onUpdate?: () => void;
    isSelected?: boolean;
    onToggleSelect?: (id: string) => void;
    onChatOpen?: (doc: any) => void;
    onPreview?: (doc: any) => void;
}> = ({ doc, onUpdate, isSelected = false, onToggleSelect, onChatOpen, onPreview }) => {
    const { currentUser } = useAuth();
    const queryClient = useQueryClient();
    const [previewOpen, setPreviewOpen] = useState(false);
    const [editOpen, setEditOpen] = useState(false);
    const [shareOpen, setShareOpen] = useState(false);
    const [commentsOpen, setCommentsOpen] = useState(false);

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

    const handleDownload = useCallback(async () => {
        const token = localStorage.getItem('token');
        const response = await fetch(`${BASE_URL}/documents/${doc.id}/download`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!response.ok) return;
        const blob = await response.blob();
        const disposition = response.headers.get('Content-Disposition') ?? '';
        const match = disposition.match(/filename="(.+?)"/);
        const filename = match ? match[1] : doc.title;
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url; link.download = filename;
        document.body.appendChild(link); link.click(); link.remove();
        URL.revokeObjectURL(url);
    }, [doc.id, doc.title]);

    const tags: string[] = doc.doc_metadata?.tags || [];
    const dateStr = doc.created_at
        ? new Date(doc.created_at).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' })
        : '';

    return (
        <>
            <div
                className={`doc-row${isSelected ? ' selected' : ''}`}
                draggable
                onDragStart={(e) => {
                    e.dataTransfer.setData('application/x-doc-id', doc.id);
                    e.dataTransfer.setData('application/x-doc-title', doc.title);
                    e.dataTransfer.effectAllowed = 'copy';
                }}
            >
                {/* Checkbox */}
                {onToggleSelect && (
                    <div
                        className={`doc-checkbox-inline${isSelected ? ' selected' : ''}`}
                        onClick={() => onToggleSelect(doc.id)}
                        title="Seleziona"
                    />
                )}

                {/* Title + AI badge */}
                <div className="doc-row-title">
                    <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', gap: '4px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span className="doc-row-name" title={doc.title}>{doc.title}</span>
                            {doc.relevance_score != null && (
                                <span className="relevance-badge" style={{ fontSize: '0.7rem', color: '#10b981', background: 'rgba(16, 185, 129, 0.15)', padding: '2px 6px', borderRadius: '10px', fontWeight: 'bold' }}>
                                    {doc.relevance_score}% Match
                                </span>
                            )}
                        </div>
                        {doc.highlight_snippet && (
                            <div
                                className="doc-row-snippet"
                                dangerouslySetInnerHTML={{ __html: doc.highlight_snippet }}
                            />
                        )}
                    </div>
                    <IndexBadge isIndexed={doc.is_indexed} />
                </div>

                {/* Tags */}
                <div className="doc-row-tags">
                    {tags.slice(0, 3).map((t: string) => (
                        <span key={t} className="tag-pill">{t}</span>
                    ))}
                </div>

                {/* Date */}
                <div className="doc-row-meta">
                    <Calendar size={13} />
                    <span>{dateStr}</span>
                </div>

                {/* Actions */}
                <div className="doc-row-actions">
                    <button onClick={() => onPreview ? onPreview(doc) : setPreviewOpen(true)} title="Anteprima" className="icon-btn"><Eye size={16} /></button>
                    <button onClick={handleDownload} title="Scarica" className="icon-btn"><FileDown size={16} /></button>
                    {onChatOpen && (
                        <button onClick={() => onChatOpen({ id: doc.id, title: doc.title })} title="Chiedi all'AI" className="icon-btn">
                            <Bot size={16} />
                        </button>
                    )}
                    {canEdit && (
                        <button onClick={() => setEditOpen(true)} title="Modifica" className="icon-btn"><Pencil size={16} /></button>
                    )}
                    <button onClick={() => setShareOpen(true)} title="Condividi" className="icon-btn"><Share2 size={16} /></button>
                    <button onClick={() => setCommentsOpen(true)} title="Commenti" className="icon-btn"><MessageSquare size={16} /></button>
                    {canEdit && (
                        <button
                            onClick={() => { if (window.confirm('Spostare nel cestino?')) softDeleteMutation.mutate(doc.id); }}
                            title="Cestino" className="icon-btn icon-btn-danger"
                        >
                            <Trash2 size={16} />
                        </button>
                    )}
                </div>
            </div>

            <DocumentPreviewModal isOpen={previewOpen} doc={doc} onClose={() => setPreviewOpen(false)} />
            {editOpen && canEdit && (
                <EditMetadataModal
                    isOpen={editOpen}
                    doc={doc}
                    onClose={() => setEditOpen(false)}
                    onSaveSuccess={() => { setEditOpen(false); onUpdate?.(); }}
                />
            )}
            {shareOpen && <ShareModal docId={doc.id} fileName={doc.title} onClose={() => setShareOpen(false)} />}
            {commentsOpen && <CommentsPanel docId={doc.id} docTitle={doc.title} onClose={() => setCommentsOpen(false)} />}
        </>
    );
};

export default DocumentRow;
