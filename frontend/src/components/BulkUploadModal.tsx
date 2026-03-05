import React, { useState } from 'react';
import { X } from 'lucide-react';
import api from '../services/api';

const BulkUploadModal: React.FC<{ onClose: () => void, onSuccess: () => void }> = ({ onClose, onSuccess }) => {
    const [files, setFiles] = useState<File[]>([]);
    const [isRestricted, setIsRestricted] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState({ total: 0, current: 0 });
    const [errors, setErrors] = useState<string[]>([]);

    // Filtro nativo supportato anche server-side
    const allowedTypes = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp"
    ];

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            // Converte FileList in Array e filtra preventivamente i tipi sul client per UX veloce
            const fileArray = Array.from(e.target.files);
            const validFiles = fileArray.filter(f => allowedTypes.includes(f.type) || f.name.endsWith('.txt')); // Fallback base per txt

            if (fileArray.length !== validFiles.length) {
                setErrors([`Attenzione: sono stati ignorati ${fileArray.length - validFiles.length} file con formato non supportato dalla cartella.`]);
            } else {
                setErrors([]);
            }

            setFiles(validFiles);
            setUploadProgress({ total: validFiles.length, current: 0 });
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (files.length === 0) return;

        setIsUploading(true);
        let currentErrorMessages: string[] = [...errors];
        let successCount = 0;

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const formData = new FormData();
            formData.append('file', file);
            // Usiamo il nome piallato/relativo come titolo
            formData.append('title', file.name);
            formData.append('is_restricted', isRestricted.toString());
            formData.append('metadata_json', JSON.stringify({ tags: ['bulk-upload'] }));

            try {
                await api.post('/documents/upload', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                successCount++;
            } catch (err: any) {
                console.error(`Upload failed for ${file.name}`, err);
                let errorMessage = 'Errore sconosciuto';

                if (err.response) {
                    // Errore dal server (4xx, 5xx)
                    errorMessage = err.response.data?.detail || `Errore server (${err.response.status})`;
                } else if (err.request) {
                    // Richiesta inviata ma nessuna risposta (problema di rete)
                    errorMessage = 'Nessuna risposta dal server (Network Error)';
                } else {
                    errorMessage = err.message;
                }

                currentErrorMessages.push(`Impossibile caricare "${file.name}": ${errorMessage}`);
            }

            setUploadProgress(prev => ({ ...prev, current: prev.current + 1 }));
            setErrors([...currentErrorMessages]);
        }

        setIsUploading(false);

        // Se almeno uno ha successo, notifichiamo il padre di ricaricare (magari con delay)
        if (successCount > 0 && currentErrorMessages.length === 0) {
            onSuccess();
        } else if (successCount > 0) {
            // In caso di errori parziali non chiudiamo la modale brutalmente ma mostriamo gli errori
            // Lo user dovra' premere la "X" dopo averli letti
        }
    };

    return (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
            <div className="auth-card" style={{ margin: 0, position: 'relative', width: '90%', maxWidth: '500px' }}>
                <button onClick={onClose} style={{ position: 'absolute', right: '1rem', top: '1rem', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                    <X />
                </button>
                <h2 style={{ marginBottom: '1.5rem' }}>Caricamento Multiplo (Seleziona Cartella)</h2>

                <form onSubmit={handleSubmit}>
                    <div style={{ marginBottom: '1rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
                            Seleziona la cartella locale da analizzare e importare
                        </label>
                        <input
                            type="file"
                            className="input"
                            style={{ border: '1px dashed var(--glass)', padding: '2rem', height: 'auto', cursor: 'pointer' }}
                            // @ts-ignore - webkitdirectory is non-standard but widely supported
                            webkitdirectory="true"
                            directory=""
                            onChange={handleFileChange}
                            required
                            disabled={isUploading}
                        />
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                            Verranno inglobati solo i formati supportati: PDF, DOCX, TXT, Immagini.
                        </div>
                    </div>

                    <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <input type="checkbox" checked={isRestricted} onChange={e => setIsRestricted(e.target.checked)} id="restricted-bulk" disabled={isUploading} />
                        <label htmlFor="restricted-bulk" style={{ fontSize: '0.875rem' }}>Marca tutti questi documenti come Riservati</label>
                    </div>

                    {files.length > 0 && (
                        <div style={{ marginBottom: '1rem', fontSize: '0.875rem', fontWeight: 600 }}>
                            {files.length} documenti pronti al caricamento.
                        </div>
                    )}

                    {isUploading && (
                        <div style={{ marginBottom: '1rem' }}>
                            <div style={{ fontSize: '0.875rem', marginBottom: '0.5rem', color: 'var(--primary)' }}>
                                Caricamento in corso: {uploadProgress.current} su {uploadProgress.total} file elaborati...
                            </div>
                            <div style={{ width: '100%', height: '8px', background: 'var(--glass)', borderRadius: '4px', overflow: 'hidden' }}>
                                <div style={{
                                    height: '100%',
                                    background: 'var(--primary)',
                                    width: `${uploadProgress.total > 0 ? (uploadProgress.current / uploadProgress.total) * 100 : 0}%`,
                                    transition: 'width 0.3s ease'
                                }}></div>
                            </div>
                        </div>
                    )}

                    {errors.length > 0 && (
                        <div style={{ marginBottom: '1rem', padding: '0.75rem', backgroundColor: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', borderRadius: '0.375rem', fontSize: '0.875rem', maxHeight: '150px', overflowY: 'auto' }}>
                            <ul style={{ paddingLeft: '1.5rem', margin: 0 }}>
                                {errors.map((err, idx) => (
                                    <li key={idx} style={{ marginBottom: '0.25rem' }}>{err}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    <div style={{ display: 'flex', gap: '1rem' }}>
                        <button className="btn" type="submit" disabled={isUploading || files.length === 0} style={{ flex: 1 }}>
                            {isUploading ? 'Attendere...' : 'Avvia Importazione'}
                        </button>

                        {(isUploading || errors.length > 0) && (
                            <button className="btn" type="button" onClick={() => { onSuccess() }} disabled={isUploading} style={{ flex: 1, background: 'transparent', border: '1px solid var(--glass)', color: 'var(--text-main)' }}>
                                Chiudi ed Ricarica
                            </button>
                        )}
                    </div>
                </form>
            </div>
        </div>
    );
};

export default BulkUploadModal;
