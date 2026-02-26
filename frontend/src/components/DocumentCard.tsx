import React from 'react';
import { FileDown, Calendar, User } from 'lucide-react';
import api from '../services/api';

const DocumentCard: React.FC<{ doc: any }> = ({ doc }) => {
    const handleDownload = async () => {
        try {
            const response = await api.get(`/documents/${doc.id}/download`, {
                responseType: 'blob'
            });
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', doc.title);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            console.error('Download failed', err);
        }
    };

    return (
        <div className="doc-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                <h3 style={{ margin: 0, fontSize: '1.125rem' }}>{doc.title}</h3>
                <button onClick={handleDownload} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--accent)' }}>
                    <FileDown size={20} />
                </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                    <Calendar size={14} />
                    {new Date(doc.created_at).toLocaleDateString()}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                    <User size={14} />
                    Proprietario ID: {doc.owner_id.slice(0, 8)}...
                </div>
            </div>

            <div style={{ marginTop: '1rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {doc.doc_metadata?.tags?.map((tag: string) => (
                    <span key={tag} style={{ background: 'var(--primary)', padding: '0.2rem 0.5rem', borderRadius: '0.25rem', fontSize: '0.75rem' }}>
                        {tag}
                    </span>
                ))}
            </div>
        </div>
    );
};

export default DocumentCard;
