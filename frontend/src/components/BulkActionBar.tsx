import React from 'react';
import { Download, X, Trash2, GitCompareArrows, MessagesSquare } from 'lucide-react';
import api from '../services/api';
import CompareModal from './CompareModal';
import MultiDocChatModal from './MultiDocChatModal';

interface BulkActionBarProps {
    selectedIds: string[];
    onClearSelection: () => void;
    onSuccess?: () => void;
    /** Optional titles for the selected documents (for display in multi-doc chat) */
    selectedTitles?: string[];
}

const BulkActionBar: React.FC<BulkActionBarProps> = ({ selectedIds, onClearSelection, onSuccess, selectedTitles = [] }) => {
    const [isExporting, setIsExporting] = React.useState(false);
    const [showCompare, setShowCompare] = React.useState(false);
    const [showGroupChat, setShowGroupChat] = React.useState(false);

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
        <>
            <div className="bulk-action-bar">
                <div className="bulk-count-badge">
                    <span className="bulk-count-number">
                        {selectedIds.length}
                    </span>
                    <span>selezionati</span>
                </div>

                <div className="bulk-separator" />

                <div className="bulk-actions-group">
                    <button
                        onClick={onClearSelection}
                        disabled={isExporting}
                        className="btn-bulk-cancel"
                        title="Annulla selezione"
                    >
                        <X size={16} /> Annulla
                    </button>

                    {/* Chat di Gruppo — appare solo con ≥2 selezionati */}
                    {selectedIds.length >= 2 && (
                        <button
                            onClick={() => setShowGroupChat(true)}
                            className="btn-bulk-chat"
                            title="Avvia chat di gruppo sui documenti selezionati"
                        >
                            <MessagesSquare size={16} />
                            Chat di Gruppo
                        </button>
                    )}

                    {/* Confronta AI — appare solo con ≥2 selezionati */}
                    {selectedIds.length >= 2 && (
                        <button
                            onClick={() => setShowCompare(true)}
                            className="btn-bulk-compare"
                            title="Confronta i documenti selezionati con l'AI"
                        >
                            <GitCompareArrows size={16} />
                            Confronta AI
                        </button>
                    )}

                    <button
                        onClick={handleExport}
                        disabled={isExporting}
                        className="btn-bulk-export"
                        title="Esporta i documenti selezionati in un archivio ZIP"
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
                        className="btn-bulk-delete"
                        title="Sposta i documenti selezionati nel cestino"
                    >
                        <Trash2 size={16} />
                        Elimina
                    </button>
                </div>
            </div>

            <CompareModal
                isOpen={showCompare}
                onClose={() => setShowCompare(false)}
                documentIds={selectedIds}
            />

            <MultiDocChatModal
                isOpen={showGroupChat}
                onClose={() => setShowGroupChat(false)}
                documentIds={selectedIds}
                documentTitles={selectedTitles}
            />
        </>
    );
};

export default BulkActionBar;

