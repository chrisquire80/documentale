import React, { useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import { useAuth } from '../store/AuthContext';
import { Search, LogOut, Upload as UploadIcon, FileText } from 'lucide-react';
import DocumentCard from '../components/DocumentCard';
import UploadModal from '../components/UploadModal';
import BulkUploadModal from '../components/BulkUploadModal';

const DashboardPage: React.FC = () => {
    const [inputValue, setInputValue] = useState('');
    const [debouncedQuery, setDebouncedQuery] = useState('');
    const [isUploadOpen, setIsUploadOpen] = useState(false);
    const [isBulkOpen, setIsBulkOpen] = useState(false);
    const { logout } = useAuth();

    // Debounce search input (500ms delay)
    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedQuery(inputValue);
        }, 500);

        return () => clearTimeout(timer);
    }, [inputValue]);

    const { data: documents, isLoading, refetch } = useQuery({
        queryKey: ['documents', debouncedQuery],
        queryFn: async () => {
            const response = await api.get(`/documents/search?query=${debouncedQuery}`);
            return response.data;
        }
    });

    const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        setInputValue(e.target.value);
    }, []);

    return (
        <div>
            <nav className="nav">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <FileText className="primary" />
                    <h1 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Documentale</h1>
                </div>
                <div style={{ display: 'flex', gap: '1rem' }}>
                    <button className="btn" style={{ width: 'auto' }} onClick={() => setIsBulkOpen(true)}>
                        <UploadIcon size={18} style={{ marginRight: '0.5rem' }} />
                        Carica Intera Cartella
                    </button>
                    <button className="btn" style={{ width: 'auto', background: 'transparent', border: '1px solid var(--accent)', color: 'var(--accent)' }} onClick={() => setIsUploadOpen(true)}>
                        <UploadIcon size={18} style={{ marginRight: '0.5rem' }} />
                        Carica File
                    </button>
                    <button className="btn" style={{ width: 'auto', background: 'transparent', border: '1px solid var(--glass)' }} onClick={logout}>
                        <LogOut size={18} />
                    </button>
                </div>
            </nav>

            <main className="container">
                <div style={{ position: 'relative', marginBottom: '2rem' }}>
                    <Search style={{ position: 'absolute', left: '1rem', top: '1rem', color: 'var(--text-muted)' }} size={20} />
                    <input
                        className="input"
                        style={{ paddingLeft: '3rem', marginBottom: 0 }}
                        placeholder="Cerca documenti per titolo, tag o contenuto..."
                        value={inputValue}
                        onChange={handleSearchChange}
                    />
                </div>

                {isLoading ? (
                    <div>Caricamento...</div>
                ) : (
                    <div className="doc-grid">
                        {documents?.map((doc: any) => (
                            <DocumentCard key={doc.id} doc={doc} />
                        ))}
                        {documents?.length === 0 && (
                            <div style={{ textAlign: 'center', gridColumn: '1/-1', color: 'var(--text-muted)', marginTop: '4rem' }}>
                                Nessun documento trovato.
                            </div>
                        )}
                    </div>
                )}
            </main>

            {isUploadOpen && (
                <UploadModal
                    onClose={() => setIsUploadOpen(false)}
                    onSuccess={() => {
                        setIsUploadOpen(false);
                        refetch();
                    }}
                />
            )}

            {isBulkOpen && (
                <BulkUploadModal
                    onClose={() => setIsBulkOpen(false)}
                    onSuccess={() => {
                        setIsBulkOpen(false);
                        refetch();
                    }}
                />
            )}
        </div>
    );
};

export default DashboardPage;
