import React, { useState, useRef } from 'react';
import { X, FileText, ZoomIn, ZoomOut, Sparkles } from 'lucide-react';
import { ChatAssistant } from './ChatAssistant';
import type { ChatAssistantHandle } from './ChatAssistant';
import PdfViewer from './PdfViewer';
import type { PdfViewerHandle } from './PdfViewer';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

interface FocusViewProps {
    doc: any;
    onClose: () => void;
}

const FocusView: React.FC<FocusViewProps> = ({ doc, onClose }) => {
    const [zoom, setZoom] = useState(100);
    const [citationHighlight, setCitationHighlight] = useState<string | undefined>(undefined);
    const pdfRef = useRef<PdfViewerHandle>(null);
    const chatRef = useRef<ChatAssistantHandle>(null);

    const handleCitationClick = (docId: string, _title: string, page?: number, highlightText?: string) => {
        // Only act if the citation is for the currently open document
        if (docId !== doc.id) return;
        setCitationHighlight(highlightText);
        if (page && pdfRef.current) {
            pdfRef.current.scrollToPage(page);
        }
    };

    const isPdf = doc.file_type?.toLowerCase() === 'pdf' || doc.file_path?.toLowerCase().endsWith('.pdf') || doc.title?.toLowerCase().endsWith('.pdf');
    const isImage = ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(doc.file_type?.toLowerCase() || '') ||
        ['.jpg', '.jpeg', '.png', '.gif', '.webp'].some(ext => (doc.file_path || doc.title || '').toLowerCase().endsWith(ext));

    const token = localStorage.getItem('token');
    const previewUrl = doc.id
        ? `${BASE_URL}/documents/${doc.id}/preview?inline=true&token=${token}`
        : '';

    const aiSummary = doc.doc_metadata?.summary;

    return (
        <div className="focus-view-overlay">
            <div className={`focus-container${isPdf ? ' has-pdf' : ''}`}>
                {/* Left: Document View */}
                <div className="focus-document">
                    <div className="focus-header">
                        <button className="icon-btn" onClick={onClose} title="Chiudi">
                            <X size={20} />
                        </button>
                        <h2 className="focus-title" title={doc.title}>{doc.title}</h2>

                        <div className="focus-header-actions">
                            {aiSummary && (
                                <div className="ai-summary-badge" title={aiSummary}>
                                    <Sparkles size={16} color="#8b5cf6" />
                                    <span>AI Pronto</span>
                                </div>
                            )}
                            {isPdf && (
                                <div className="zoom-controls">
                                    <button onClick={() => setZoom(z => Math.max(50, z - 10))} className="icon-btn" title="Riduci zoom">
                                        <ZoomOut size={16} />
                                    </button>
                                    <span className="zoom-label">{zoom}%</span>
                                    <button onClick={() => setZoom(z => Math.min(200, z + 10))} className="icon-btn" title="Aumenta zoom">
                                        <ZoomIn size={16} />
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="focus-content">
                        {!previewUrl ? (
                            <div className="doc-preview-placeholder">
                                <FileText size={48} style={{ opacity: 0.2, marginBottom: '1rem' }} />
                                <p>Anteprima non disponibile.</p>
                            </div>
                        ) : isImage ? (
                            <div className="image-preview-container">
                                <img src={previewUrl} alt={doc.title} className="focus-image" />
                            </div>
                        ) : (
                            <PdfViewer
                                ref={pdfRef}
                                url={previewUrl}
                                zoom={zoom}
                                highlightText={citationHighlight}
                                onTextSelect={(text) => {
                                    chatRef.current?.sendMessage(text);
                                }}
                            />
                        )}
                    </div>
                </div>

                {/* Right: Docked Chat */}
                <div className="focus-chat">
                    <ChatAssistant
                        ref={chatRef}
                        isOpen={true}
                        onClose={onClose}
                        documentId={doc.id}
                        documentTitle={doc.title}
                        docked={true}
                        onToggleDock={() => { }}
                        onOpenDocument={handleCitationClick}
                    />
                </div>
            </div>
        </div>
    );
};

export default FocusView;
