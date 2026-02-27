import React from 'react';
import { Download, X, Trash2 } from 'lucide-react';
import api from '../services/api';

interface BulkActionBarProps {
    selectedIds: string[];
    onClearSelection: () => void;
    onSuccess?: () => void;
}

const BulkActionBar: React.FC<BulkActionBarProps> = ({ selectedIds, onClearSelection, onSuccess }) => {
    const [isExporting, setIsExporting] = React.useState(false);

    if (selectedIds.length === 0) return null;

    const handleExport = async () => {
        setIsExporting(true);
        try {
            const response = await api.post(
                '/documents/export-bulk',
                { document_ids: selectedIds },
                { responseType: 'blob' } // Important to handle ZIP blob
            );

            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'esportazione_massiva.zip');
            document.body.appendChild(link);
            link.click();
            link.parentNode?.removeChild(link);
            window.URL.revokeObjectURL(url);

            // Clear selection after successful export
            onClearSelection();
        } catch (error) {
            console.error('Export failed:', error);
            alert('Errore durante l\'esportazione.');
        } finally {
            setIsExporting(false);
        }
    };

    return (
        <div style={{
            position: 'fixed',
            bottom: '2rem',
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--accent)',
            boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
            borderRadius: '999px',
            padding: '0.75rem 1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '1.5rem',
            zIndex: 1000,
            animation: 'pageEnter 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600 }}>
                <span style={{
                    backgroundColor: 'var(--accent)',
                    color: 'var(--bg-dark)',
                    width: '24px', height: '24px',
                    borderRadius: '50%',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '0.9rem'
                }}>
                    {selectedIds.length}
                </span>
                <span>selezionati</span>
            </div>

            <div style={{ width: '1px', height: '24px', backgroundColor: 'var(--glass)' }} />

            <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button
                    onClick={onClearSelection}
                    disabled={isExporting}
                    style={{
                        display: 'flex', alignItems: 'center', gap: '0.4rem',
                        background: 'transparent',
                        color: 'var(--text-muted)',
                        border: 'none',
                        cursor: isExporting ? 'not-allowed' : 'pointer',
                        fontWeight: 500,
                        padding: '0.5rem 0.75rem',
                        borderRadius: '0.375rem',
                    }}
                >
                    <X size={16} /> Annulla
                </button>

                <button
                    onClick={handleExport}
                    disabled={isExporting}
                    style={{
                        display: 'flex', alignItems: 'center', gap: '0.4rem',
                        background: 'var(--accent)',
                        color: 'var(--bg-dark)',
                        border: 'none',
                        cursor: isExporting ? 'not-allowed' : 'pointer',
                        fontWeight: 600,
                        padding: '0.5rem 1rem',
                        borderRadius: '0.375rem',
                        transition: 'opacity 0.2s',
                        opacity: isExporting ? 0.7 : 1
                    }}
                >
                    <Download size={16} />
                    {isExporting ? 'Esportazione...' : 'Esporta ZIP'}
                </button>

                <button
                    onClick={async () => {
                        if (window.confirm(`Sei sicuro di voler spostare ${selectedIds.length} documenti nel cestino?`)) {
                            try {
                                await api.post('/documents/bulk-delete', { document_ids: selectedIds });
                                onClearSelection();
                                if (onSuccess) onSuccess();
                            } catch (err) {
                                console.error('Bulk delete failed:', err);
                                alert('Errore durante l\'eliminazione massiva.');
                            }
                        }
                    }}
                    style={{
                        display: 'flex', alignItems: 'center', gap: '0.4rem',
                        background: 'transparent',
                        color: 'var(--error)',
                        border: '1px solid var(--error)',
                        cursor: 'pointer',
                        fontWeight: 600,
                        padding: '0.5rem 1rem',
                        borderRadius: '0.375rem',
                        transition: 'all 0.2s',
                    }}
                    onMouseOver={(e) => {
                        e.currentTarget.style.background = 'var(--error)';
                        e.currentTarget.style.color = 'var(--bg-dark)';
                    }}
                    onMouseOut={(e) => {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = 'var(--error)';
                    }}
                >
                    <Trash2 size={16} />
                    Elimina
                </button>
            </div>
        </div>
    );
};

export default BulkActionBar;
