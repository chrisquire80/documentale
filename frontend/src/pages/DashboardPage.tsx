import React, { useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import { useAuth } from '../store/AuthContext';
import { Search, LogOut, Upload as UploadIcon, FileText, BarChart2 } from 'lucide-react';
import DocumentCard from '../components/DocumentCard';
import SkeletonCard from '../components/SkeletonCard';
import Pagination from '../components/Pagination';
import UploadModal from '../components/UploadModal';
import BulkUploadModal from '../components/BulkUploadModal';
import CacheStatsModal from '../components/CacheStatsModal';

const ITEMS_PER_PAGE = 20;
const SKELETON_COUNT = 6;

interface PaginatedDocuments {
    items: any[];
    total: number;
    limit: number;
    offset: number;
}

const DashboardPage: React.FC = () => {
    const [inputValue, setInputValue] = useState('');
    const [debouncedQuery, setDebouncedQuery] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const [isUploadOpen, setIsUploadOpen] = useState(false);
    const [isBulkOpen, setIsBulkOpen] = useState(false);
    const [isStatsOpen, setIsStatsOpen] = useState(false);
    const { logout } = useAuth();

    // Debounce search input (500ms delay)
    useEffect(() => {
        const timer = setTimeout(() => setDebouncedQuery(inputValue), 500);
        return () => clearTimeout(timer);
    }, [inputValue]);

    // Reset to page 1 whenever the search term changes
    useEffect(() => {
        setCurrentPage(1);
    }, [debouncedQuery]);

    const offset = (currentPage - 1) * ITEMS_PER_PAGE;

    const { data, isLoading, refetch } = useQuery<PaginatedDocuments>({
        queryKey: ['documents', debouncedQuery, currentPage],
        queryFn: async () => {
            const params = new URLSearchParams({
                query: debouncedQuery,
                limit: String(ITEMS_PER_PAGE),
                offset: String(offset),
            });
            const response = await api.get(`/documents/search?${params}`);
            return response.data;
        },
    });

    const documents = data?.items ?? [];
    const total = data?.total ?? 0;
    const totalPages = Math.max(1, Math.ceil(total / ITEMS_PER_PAGE));

    const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        setInputValue(e.target.value);
    }, []);

    const handleUploadSuccess = useCallback(() => {
        setIsUploadOpen(false);
        refetch();
    }, [refetch]);

    const handleBulkSuccess = useCallback(() => {
        setIsBulkOpen(false);
        refetch();
    }, [refetch]);

    return (
        <div>
            <nav className="nav">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <FileText className="primary" />
                    <h1 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Documentale</h1>
                </div>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                    <button className="btn" style={{ width: 'auto' }} onClick={() => setIsBulkOpen(true)}>
                        <UploadIcon size={18} style={{ marginRight: '0.5rem' }} />
                        Carica Cartella
                    </button>
                    <button
                        className="btn"
                        style={{ width: 'auto', background: 'transparent', border: '1px solid var(--accent)', color: 'var(--accent)' }}
                        onClick={() => setIsUploadOpen(true)}
                    >
                        <UploadIcon size={18} style={{ marginRight: '0.5rem' }} />
                        Carica File
                    </button>
                    <button
                        className="btn"
                        style={{ width: 'auto', background: 'transparent', border: '1px solid var(--glass)', color: 'var(--text-muted)' }}
                        onClick={() => setIsStatsOpen(true)}
                        title="Statistiche cache Redis"
                    >
                        <BarChart2 size={18} />
                    </button>
                    <button
                        className="btn"
                        style={{ width: 'auto', background: 'transparent', border: '1px solid var(--glass)' }}
                        onClick={logout}
                    >
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
                        placeholder="Cerca documenti per titolo, tag o contenuto…"
                        value={inputValue}
                        onChange={handleSearchChange}
                    />
                </div>

                {isLoading ? (
                    <div className="doc-grid">
                        {Array.from({ length: SKELETON_COUNT }).map((_, i) => (
                            <SkeletonCard key={i} />
                        ))}
                    </div>
                ) : (
                    <>
                        {/* key forces CSS page-enter animation on page/query change */}
                        <div className="doc-grid" key={`${currentPage}-${debouncedQuery}`}>
                            {documents.map((doc: any) => (
                                <DocumentCard key={doc.id} doc={doc} />
                            ))}
                            {documents.length === 0 && (
                                <div style={{ textAlign: 'center', gridColumn: '1/-1', color: 'var(--text-muted)', marginTop: '4rem' }}>
                                    Nessun documento trovato.
                                </div>
                            )}
                        </div>

                        <Pagination
                            currentPage={currentPage}
                            totalPages={totalPages}
                            total={total}
                            onPageChange={setCurrentPage}
                        />
                    </>
                )}
            </main>

            {isUploadOpen && (
                <UploadModal onClose={() => setIsUploadOpen(false)} onSuccess={handleUploadSuccess} />
            )}
            {isBulkOpen && (
                <BulkUploadModal onClose={() => setIsBulkOpen(false)} onSuccess={handleBulkSuccess} />
            )}
            {isStatsOpen && (
                <CacheStatsModal onClose={() => setIsStatsOpen(false)} />
            )}
        </div>
    );
};

export default DashboardPage;
