import React, { useState, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { FileDown, Calendar, Eye, Pencil, Share2, Bot, Trash2, MessageSquare, Sparkles, AlertTriangle, HelpCircle, Link2, CheckCircle } from 'lucide-react';
import DocumentPreviewModal from './DocumentPreviewModal';
import RelatedDocumentsModal from './RelatedDocumentsModal';
import ConflictResolutionModal from './ConflictResolutionModal';
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
    const [relatedOpen, setRelatedOpen] = useState(false);
    const [conflictOpen, setConflictOpen] = useState(false);

    const canEdit = (currentUser?.role as string) === 'ADMIN' || currentUser?.id === doc.owner_id;

    const softDeleteMutation = useMutation({
        mutationFn: (docId: string) => {
            const token = localStorage.getItem('token');
            return axios.delete(`${BASE_URL}/documents/${docId}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
            if (onUpdate) onUpdate();
        }
    });

    const approveTagMutation = useMutation({
        mutationFn: ({ tagId }: { tagId: string }) => {
            const token = localStorage.getItem('token');
            return axios.post(`${BASE_URL}/documents/${doc.id}/tags/${tagId}/approve`, {}, {
                headers: { Authorization: `Bearer ${token}` }
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
            if (onUpdate) onUpdate();
        }
    });

    const rejectTagMutation = useMutation({
        mutationFn: ({ tagId }: { tagId: string }) => {
            const token = localStorage.getItem('token');
            return axios.delete(`${BASE_URL}/documents/${doc.id}/tags/${tagId}`, {
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
                            {doc.category && (
                                <span style={{ fontSize: '0.65rem', color: '#60a5fa', background: 'rgba(96, 165, 250, 0.1)', padding: '1px 5px', borderRadius: '4px', border: '1px solid rgba(96, 165, 250, 0.2)', fontWeight: 600, textTransform: 'uppercase' }}>
                                    {doc.category}
                                </span>
                            )}
                            {doc.status === 'validated' && (
                                <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase', background: 'rgba(16, 185, 129, 0.1)', padding: '1px 6px', borderRadius: '4px' }}>
                                    <CheckCircle size={12} /> Validato
                                </span>
                            )}
                            {doc.relevance_score != null && (
                                <span className="relevance-badge" style={{ fontSize: '0.7rem', color: '#10b981', background: 'rgba(16, 185, 129, 0.15)', padding: '2px 6px', borderRadius: '10px', fontWeight: 'bold' }}>
                                    {doc.relevance_score}% Match
                                </span>
                            )}
                            {doc.conflicts && doc.conflicts.some((c: any) => c.status === 'pending') && (
                                <span className="conflict-badge pulse" title="Rilevati conflitti semantici con altri documenti" style={{ fontSize: '0.65rem', color: '#fff', background: '#ef4444', padding: '1px 6px', borderRadius: '4px', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '3px' }}>
                                    <AlertTriangle size={10} /> Conflitti
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
                    {/* Relational Tags (from newest version) */}
                    {doc.versions && doc.versions.length > 0 && doc.versions[0].tags?.slice(0, 3).map((t: any) => (
                        <span
                            key={t.tag.id}
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.25rem',
                                background: (t.status === 'suggested' && doc.status !== 'validated') ? 'rgba(56, 189, 248, 0.08)' : 'var(--primary)',
                                border: (t.status === 'suggested' && doc.status !== 'validated') ? '1px dashed #38bdf8' : '1px solid transparent',
                                color: (t.status === 'suggested' && doc.status !== 'validated') ? '#38bdf8' : t.status === 'validated' ? '#10b981' : 'var(--text-main)',
                                padding: '0.15rem 0.4rem',
                                borderRadius: '0.25rem',
                                fontSize: '0.72rem',
                                fontWeight: t.status === 'validated' || doc.status === 'validated' ? 600 : 400
                            }}
                            title={t.is_ai_generated ? `AI Suggestion${t.page_number ? ` (p. ${t.page_number})` : ''}${t.confidence ? ` - Confidence: ${(t.confidence * 100).toFixed(0)}%` : ''}${t.ai_reasoning ? `\n\nReasoning: ${t.ai_reasoning}` : ''}` : "Confirmed Tag"}
                        >
                            {t.is_ai_generated && <Sparkles size={11} />}
                            {t.tag.name}
                            {t.is_ai_generated && t.ai_reasoning && <HelpCircle size={10} style={{ opacity: 0.6 }} />}
                            {t.status === 'suggested' && canEdit && (
                                <div style={{ display: 'flex', gap: '2px', marginLeft: '4px', borderLeft: '1px solid rgba(56, 189, 248, 0.3)', paddingLeft: '4px' }}>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); approveTagMutation.mutate({ tagId: t.tag.id }); }}
                                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#10b981', padding: '0', fontSize: '12px', fontWeight: 'bold' }}
                                        title="Approve"
                                    >✓</button>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); rejectTagMutation.mutate({ tagId: t.tag.id }); }}
                                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444', padding: '0', fontSize: '12px', fontWeight: 'bold' }}
                                        title="Reject"
                                    >×</button>
                                </div>
                            )}
                        </span>
                    ))}
                    {/* Fallback to legacy tags if no relational tags */}
                    {(!doc.versions || doc.versions.length === 0 || !doc.versions[0].tags || doc.versions[0].tags.length === 0) && tags.slice(0, 3).map((t: string) => (
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
                    <button onClick={() => setRelatedOpen(true)} title="Documenti Correlati" className="icon-btn">
                        <Link2 size={16} />
                    </button>
                    {doc.conflicts && doc.conflicts.some((c: any) => c.status === 'pending') && (
                        <button onClick={() => setConflictOpen(true)} title="Risolvi Conflitti" className="icon-btn" style={{ color: '#ef4444' }}>
                            <AlertTriangle size={16} />
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
            {relatedOpen && (
                <RelatedDocumentsModal
                    isOpen={relatedOpen}
                    onClose={() => setRelatedOpen(false)}
                    docId={doc.id}
                    docTitle={doc.title}
                />
            )}
            {conflictOpen && (
                <ConflictResolutionModal
                    isOpen={conflictOpen}
                    onClose={() => setConflictOpen(false)}
                    doc={doc}
                />
            )}
            {shareOpen && <ShareModal docId={doc.id} fileName={doc.title} onClose={() => setShareOpen(false)} />}
            {commentsOpen && <CommentsPanel docId={doc.id} docTitle={doc.title} onClose={() => setCommentsOpen(false)} />}
        </>
    );
};

export default DocumentRow;
