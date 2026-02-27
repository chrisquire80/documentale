import React from 'react';
import { X } from 'lucide-react';

interface DocumentPreviewModalProps {
    isOpen: boolean;
    onClose: () => void;
    doc: any;
}

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

const DocumentPreviewModal: React.FC<DocumentPreviewModalProps> = ({ isOpen, onClose, doc }) => {
    if (!isOpen || !doc) return null;

    const token = localStorage.getItem('token');
    const previewUrl = `${BASE_URL}/documents/${doc.id}/download?inline=true&token=${token}`;

    // Attempt to guess extension from title if no explicit extension
    const filename = doc.title.toLowerCase();

    // Find metadata tags if any to help identify
    const tags = doc.doc_metadata?.tags || [];

    let isImage = /\.(jpg|jpeg|png|gif|webp)$/i.test(filename);

    // If no extension in title, just assume we can try an iframe, but images might need an <img> tag.
    // Usually Documentale appends the extension during download but let's test these cases.
    // Actually the download route uses proper content-type, so an iframe works well for BOTH pdf and images!
    // However, <img> gives better control for images. Let's use iframe for PDF, and img for images.

    // If we only know it's not a word document:
    const isWord = /\.(doc|docx)$/i.test(filename) || tags.includes('word');
    const isText = /\.(txt)$/i.test(filename) || tags.includes('text');

    const isSupported = !isWord && !isText; // Let's try to preview everything except word/txt which usually download

    return (
        <div className="modal-overlay" onClick={onClose} style={{ zIndex: 1000 }}>
            <div
                className="modal-content preview-modal"
                onClick={e => e.stopPropagation()}
                style={{
                    width: '90vw',
                    maxWidth: '1200px',
                    height: '90vh',
                    display: 'flex',
                    flexDirection: 'column',
                    padding: '1rem',
                }}
            >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <h2 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--text)' }}>Anteprima: {doc.title}</h2>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text)' }}>
                        <X size={24} />
                    </button>
                </div>

                <div style={{
                    flex: 1,
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    backgroundColor: '#e5e7eb',
                    borderRadius: '8px',
                    overflow: 'hidden'
                }}>
                    {!isSupported ? (
                        <div style={{ textAlign: 'center', color: '#4b5563' }}>
                            <p style={{ marginBottom: '1rem' }}>L'anteprima in-browser non è disponibile per i documenti Office o di testo semplice.</p>
                            <a href={previewUrl.replace('inline=true', 'inline=false')} className="btn" style={{ background: 'var(--primary)', color: 'white', textDecoration: 'none', padding: '0.5rem 1rem', borderRadius: '4px' }}>
                                Scarica il file
                            </a>
                        </div>
                    ) : isImage ? (
                        <img
                            src={previewUrl}
                            alt={`Anteprima ${doc.title}`}
                            style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
                        />
                    ) : (
                        <iframe
                            src={previewUrl}
                            style={{ width: '100%', height: '100%', border: 'none', backgroundColor: 'white' }}
                            title={`Anteprima PDF ${doc.title}`}
                        />
                    )}
                </div>
            </div>
        </div>
    );
};

export default DocumentPreviewModal;
