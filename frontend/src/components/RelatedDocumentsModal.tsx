import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { X, Calendar, FileText } from 'lucide-react';
import api from '../services/api';

interface RelatedDocumentsModalProps {
    isOpen: boolean;
    onClose: () => void;
    docId: string;
    docTitle: string;
}

const RelatedDocumentsModal: React.FC<RelatedDocumentsModalProps> = ({ isOpen, onClose, docId, docTitle }) => {
    const { data: relatedDocs, isLoading, error } = useQuery({
        queryKey: ['documents', docId, 'related'],
        queryFn: async () => {
            const res = await api.get(`/api/documents/${docId}/related?limit=5`);
            return res.data;
        },
        enabled: isOpen,
    });

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose} style={{ zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div
                className="modal-content"
                onClick={e => e.stopPropagation()}
                style={{
                    width: '90vw',
                    maxWidth: '600px',
                    maxHeight: '80vh',
                    display: 'flex',
                    flexDirection: 'column',
                    padding: '1.5rem',
                    backgroundColor: 'var(--bg-card)',
                    borderRadius: '12px',
                    boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
                }}
            >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h2 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--text)' }}>
                        <span style={{ color: 'var(--text-muted)', fontSize: '1rem', fontWeight: 'normal', display: 'block', marginBottom: '4px' }}>Documenti correlati a:</span>
                        {docTitle}
                    </h2>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text)' }}>
                        <X size={24} />
                    </button>
                </div>

                <div style={{ flex: 1, overflowY: 'auto', paddingRight: '0.5rem' }}>
                    {isLoading ? (
                        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                            Ricerca similarità semantica in corso...
                        </div>
                    ) : error ? (
                        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--error)' }}>
                            Errore durante il caricamento dei documenti correlati.
                        </div>
                    ) : relatedDocs?.length === 0 ? (
                        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                            Nessun documento simile trovato.
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            {relatedDocs?.map((rdoc: any) => (
                                <div key={rdoc.id} style={{
                                    padding: '1rem',
                                    border: '1px solid var(--border)',
                                    borderRadius: '8px',
                                    backgroundColor: 'var(--bg-main)',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    gap: '0.75rem',
                                    transition: 'border-color 0.2s',
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600, color: 'var(--text)' }}>
                                            <FileText size={18} color="var(--accent)" />
                                            {rdoc.title}
                                        </div>
                                    </div>
                                    <div style={{ display: 'flex', gap: '1rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                            <Calendar size={14} />
                                            {new Date(rdoc.created_at).toLocaleDateString('it-IT')}
                                        </span>
                                        {rdoc.metadata_entries?.[0]?.metadata_json?.author && (
                                            <span>
                                                Autore: {rdoc.metadata_entries[0].metadata_json.author}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default RelatedDocumentsModal;
