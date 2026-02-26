import React, { useState, useEffect } from 'react';
import { X, Save, AlertCircle } from 'lucide-react';

interface EditMetadataModalProps {
    isOpen: boolean;
    onClose: () => void;
    doc: any;
    onSaveSuccess: () => void;
}

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

const EditMetadataModal: React.FC<EditMetadataModalProps> = ({ isOpen, onClose, doc, onSaveSuccess }) => {
    const [title, setTitle] = useState('');
    const [department, setDepartment] = useState('');
    const [author, setAuthor] = useState('');
    const [tagsInput, setTagsInput] = useState('');
    const [isRestricted, setIsRestricted] = useState(false);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Initialize state with current document data when modal opens
    useEffect(() => {
        if (isOpen && doc) {
            setTitle(doc.title || '');
            setIsRestricted(doc.is_restricted || false);

            const meta = doc.doc_metadata || {};
            setDepartment(meta.dept || '');
            setAuthor(meta.author || '');

            const tags = meta.tags || [];
            if (Array.isArray(tags)) {
                setTagsInput(tags.join(', '));
            } else {
                setTagsInput(tags);
            }

            setError(null);
        }
    }, [isOpen, doc]);

    if (!isOpen || !doc) return null;

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        // Process tags
        const tagsArray = tagsInput
            .split(',')
            .map(t => t.trim())
            .filter(t => t.length > 0);

        const updateData = {
            title: title.trim(),
            is_restricted: isRestricted,
            doc_metadata: {
                ...doc.doc_metadata,
                dept: department.trim(),
                author: author.trim(),
                tags: tagsArray
            }
        };

        try {
            const token = localStorage.getItem('token');
            const res = await fetch(`${BASE_URL}/documents/${doc.id}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {})
                },
                body: JSON.stringify(updateData)
            });

            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.detail || `Errore HTTP ${res.status}`);
            }

            onSaveSuccess();
            onClose();
        } catch (err: any) {
            setError(err.message || 'Si è verificato un errore durante il salvataggio.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose} style={{ zIndex: 1000 }}>
            <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '500px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h2 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--text)' }}>Modifica Metadati</h2>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text)' }}>
                        <X size={24} />
                    </button>
                </div>

                {error && (
                    <div style={{ padding: '0.75rem', marginBottom: '1rem', backgroundColor: 'rgba(239, 68, 68, 0.1)', borderLeft: '4px solid var(--error)', color: 'var(--error)', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <AlertCircle size={18} />
                        <span>{error}</span>
                    </div>
                )}

                <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Titolo</label>
                        <input
                            type="text"
                            required
                            name="docTitle"
                            className="input"
                            value={title}
                            onChange={e => setTitle(e.target.value)}
                        />
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Dipartimento</label>
                            <input
                                type="text"
                                className="input"
                                name="docDept"
                                value={department}
                                onChange={e => setDepartment(e.target.value)}
                                placeholder="es. HR, IT, Finance"
                            />
                        </div>
                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Autore / Ente</label>
                            <input
                                type="text"
                                className="input"
                                name="docAuthor"
                                value={author}
                                onChange={e => setAuthor(e.target.value)}
                                placeholder="es. Mario Rossi"
                            />
                        </div>
                    </div>

                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Tags (separati da virgola)</label>
                        <input
                            type="text"
                            className="input"
                            name="docTags"
                            value={tagsInput}
                            onChange={e => setTagsInput(e.target.value)}
                            placeholder="es. contratto, fattura, urgente"
                        />
                    </div>

                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem', cursor: 'pointer' }}>
                        <input
                            type="checkbox"
                            checked={isRestricted}
                            onChange={e => setIsRestricted(e.target.checked)}
                            style={{ width: '1.2rem', height: '1.2rem' }}
                        />
                        <span style={{ fontWeight: 500 }}>Documento Riservato</span>
                    </label>
                    <p style={{ margin: '-0.5rem 0 0 1.7rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        Solo visibile al proprietario e agli amministratori.
                    </p>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
                        <button type="button" onClick={onClose} className="btn" style={{ background: 'transparent', color: 'var(--text)', border: '1px solid var(--border)' }}>
                            Annulla
                        </button>
                        <button type="submit" disabled={loading} className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <Save size={18} />
                            {loading ? 'Salvataggio...' : 'Salva Modifiche'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default EditMetadataModal;
