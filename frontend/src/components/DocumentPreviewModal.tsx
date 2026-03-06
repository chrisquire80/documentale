import React, { useRef } from 'react';
import { X, Sparkles, BookOpen } from 'lucide-react';
import PdfViewer from './PdfViewer';
import type { PdfViewerHandle } from './PdfViewer';
import DeepAnalysisPanel from './DeepAnalysisPanel';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

interface DocumentPreviewModalProps {
    isOpen: boolean;
    onClose: () => void;
    doc: any;
}

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

const DocumentPreviewModal: React.FC<DocumentPreviewModalProps> = ({ isOpen, onClose, doc }) => {
    const queryClient = useQueryClient();
    const pdfRef = useRef<PdfViewerHandle>(null);

    if (!isOpen || !doc) return null;

    const token = localStorage.getItem('token');
    const previewUrl = `${BASE_URL}/documents/${doc.id}/download?inline=true&token=${token}`;
    const filename = doc.title.toLowerCase();

    const tags = doc.doc_metadata?.tags || [];
    const isImage = /\.(jpg|jpeg|png|gif|webp)$/i.test(filename);
    const isWord = /\.(doc|docx)$/i.test(filename) || tags.includes('word');
    const isText = /\.(txt)$/i.test(filename) || tags.includes('text');
    const isSupported = !isWord && !isText;

    const [activeTab, setActiveTab] = React.useState<'preview' | 'analysis'>('preview');

    const approveTagMutation = useMutation({
        mutationFn: ({ tagId }: { versionId: string, tagId: string }) => {
            return axios.post(`${BASE_URL}/documents/${doc.id}/tags/${tagId}/approve`, {}, {
                headers: { Authorization: `Bearer ${token}` }
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
        }
    });

    const rejectTagMutation = useMutation({
        mutationFn: ({ tagId }: { versionId: string, tagId: string }) => {
            return axios.delete(`${BASE_URL}/documents/${doc.id}/tags/${tagId}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
        }
    });

    const handleJumpToPage = (page: number) => {
        setActiveTab('preview');
        // Usiamo un piccolo timeout per assicurarci che il componente sia montato/visibile
        setTimeout(() => {
            pdfRef.current?.scrollToPage(page);
        }, 100);
    };

    return (
        <div className="modal-overlay" onClick={onClose} style={{ zIndex: 1000 }}>
            <div
                className="modal-content preview-modal"
                onClick={e => e.stopPropagation()}
                style={{
                    width: '95vw',
                    maxWidth: '1400px',
                    height: '92vh',
                    display: 'flex',
                    flexDirection: 'column',
                    padding: 0,
                    overflow: 'hidden'
                }}
            >
                {/* Header Premium */}
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '1rem 1.5rem',
                    background: 'var(--bg-card)',
                    borderBottom: '1px solid var(--glass)'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                        <h2 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 600 }}>{doc.title}</h2>
                        <div className="preview-tabs" style={{ display: 'flex', gap: '4px', background: 'rgba(0,0,0,0.2)', padding: '4px', borderRadius: '8px' }}>
                            <button
                                onClick={() => setActiveTab('preview')}
                                style={{
                                    padding: '0.4rem 1rem',
                                    borderRadius: '6px',
                                    border: 'none',
                                    background: activeTab === 'preview' ? 'var(--accent)' : 'transparent',
                                    color: activeTab === 'preview' ? 'var(--bg-dark)' : 'var(--text-muted)',
                                    cursor: 'pointer',
                                    fontWeight: 600,
                                    fontSize: '0.85rem',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '6px'
                                }}
                            >
                                <BookOpen size={16} /> Visore
                            </button>
                            <button
                                onClick={() => setActiveTab('analysis')}
                                style={{
                                    padding: '0.4rem 1rem',
                                    borderRadius: '6px',
                                    border: 'none',
                                    background: activeTab === 'analysis' ? 'var(--accent)' : 'transparent',
                                    color: activeTab === 'analysis' ? 'var(--bg-dark)' : 'var(--text-muted)',
                                    cursor: 'pointer',
                                    fontWeight: 600,
                                    fontSize: '0.85rem',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '6px'
                                }}
                            >
                                <Sparkles size={16} /> Deep Analysis
                            </button>
                        </div>
                    </div>
                    <button onClick={onClose} title="Chiudi" style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text)' }}>
                        <X size={24} />
                    </button>
                </div>

                <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                    {/* Left side: Content / Preview */}
                    <div style={{
                        flex: activeTab === 'preview' ? 1 : 0,
                        display: activeTab === 'preview' ? 'flex' : 'none',
                        background: '#e5e7eb',
                        position: 'relative'
                    }}>
                        {!isSupported ? (
                            <div style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', color: '#4b5563' }}>
                                <div style={{ textAlign: 'center' }}>
                                    <p>Anteprima non disponibile per questo formato.</p>
                                    <a href={previewUrl.replace('inline=true', 'inline=false')} className="btn">Scarica</a>
                                </div>
                            </div>
                        ) : isImage ? (
                            <img src={previewUrl} alt={doc.title} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', margin: 'auto' }} />
                        ) : (
                            <PdfViewer ref={pdfRef} url={previewUrl} zoom={100} />
                        )}
                    </div>

                    {/* Right side: Deep Analysis (or full width if selected) */}
                    <div style={{
                        flex: activeTab === 'analysis' ? 1 : 0.35,
                        display: 'flex',
                        flexDirection: 'column',
                        borderLeft: '1px solid var(--glass)',
                        background: 'var(--bg-dark)',
                        overflowY: 'auto',
                        minWidth: activeTab === 'analysis' ? '100%' : '400px',
                        transition: 'all 0.3s ease'
                    }}>
                        <DeepAnalysisPanel
                            doc={doc}
                            onApproveTag={(versionId, tagId) => approveTagMutation.mutate({ versionId, tagId })}
                            onRejectTag={(versionId, tagId) => rejectTagMutation.mutate({ versionId, tagId })}
                            onJumpToPage={handleJumpToPage}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DocumentPreviewModal;
