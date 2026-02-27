import React, { useState, useEffect, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { useAuth } from '../store/AuthContext';
import { Search, LogOut, Upload as UploadIcon, FileText, BarChart2, Trash2, SlidersHorizontal } from 'lucide-react';
import DocumentCard from '../components/DocumentCard';
import SkeletonCard from '../components/SkeletonCard';
import Pagination from '../components/Pagination';
import UploadModal from '../components/UploadModal';
import BulkUploadModal from '../components/BulkUploadModal';
import CacheStatsModal from '../components/CacheStatsModal';
import FilterSidebar, { Filters } from '../components/FilterSidebar';
import TrashModal from '../components/TrashModal';
import StatsWidget from '../components/StatsWidget';

const ITEMS_PER_PAGE = 20;
const SKELETON_COUNT = 6;

interface PaginatedDocuments {
    items: any[];
    total: number;
    limit: number;
    offset: number;
}

const EMPTY_FILTERS: Filters = { file_type: '', date_from: '', date_to: '' };

const DashboardPage: React.FC = () => {
    const queryClient = useQueryClient();
    const [inputValue, setInputValue] = useState('');
    const [debouncedQuery, setDebouncedQuery] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
    const [showFilters, setShowFilters] = useState(false);

    const [isUploadOpen, setIsUploadOpen] = useState(false);
    const [isBulkOpen, setIsBulkOpen] = useState(false);
    const [isStatsOpen, setIsStatsOpen] = useState(false);
    const [isDocStatsOpen, setIsDocStatsOpen] = useState(false);
    const [isTrashOpen, setIsTrashOpen] = useState(false);

    const { logout } = useAuth();

    // Debounce
    useEffect(() => {
        const timer = setTimeout(() => setDebouncedQuery(inputValue), 500);
        return () => clearTimeout(timer);
    }, [inputValue]);

    // Reset pagina su cambio query/filtri
    useEffect(() => { setCurrentPage(1); }, [debouncedQuery, filters]);

    const offset = (currentPage - 1) * ITEMS_PER_PAGE;

    const { data, isLoading, refetch } = useQuery<PaginatedDocuments>({
        queryKey: ['documents', debouncedQuery, currentPage, filters],
        queryFn: async () => {
            const params = new URLSearchParams({
                limit: String(ITEMS_PER_PAGE),
                offset: String(offset),
            });
            if (debouncedQuery) params.set('query', debouncedQuery);
            if (filters.file_type) params.set('file_type', filters.file_type);
            if (filters.date_from) params.set('date_from', filters.date_from);
            if (filters.date_to) params.set('date_to', filters.date_to);
            const response = await api.get(`/documents/search?${params}`);
            return response.data;
        },
    });

    const [documents, setDocuments] = useState<any[]>([]);

    useEffect(() => {
        if (data?.items) setDocuments(data.items);
    }, [data]);

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

    const handleDocDeleted = useCallback((id: string) => {
        setDocuments((prev) => prev.filter((d) => d.id !== id));
        queryClient.invalidateQueries({ queryKey: ['trash'] });
    }, [queryClient]);

    const handleDocUpdated = useCallback((updated: any) => {
        setDocuments((prev) => prev.map((d) => d.id === updated.id ? updated : d));
    }, []);

    const hasActiveFilters = filters.file_type || filters.date_from || filters.date_to;

    return (
        <div>
            {/* ── Navbar ── */}
            <nav className="nav">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <FileText className="primary" />
                    <h1 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Documentale</h1>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                    <button className="btn" style={{ width: 'auto' }} onClick={() => setIsBulkOpen(true)}>
                        <UploadIcon size={16} style={{ marginRight: '0.4rem' }} />
                        Cartella
                    </button>
                    <button
                        className="btn"
                        style={{ width: 'auto', background: 'transparent', border: '1px solid var(--accent)', color: 'var(--accent)' }}
                        onClick={() => setIsUploadOpen(true)}
                    >
                        <UploadIcon size={16} style={{ marginRight: '0.4rem' }} />
                        File
                    </button>
                    <button
                        className="btn"
                        style={{ width: 'auto', background: 'transparent', border: `1px solid ${hasActiveFilters ? 'var(--accent)' : 'var(--glass)'}`, color: hasActiveFilters ? 'var(--accent)' : 'var(--text-muted)' }}
                        onClick={() => setShowFilters((v) => !v)}
                        title="Filtri"
                    >
                        <SlidersHorizontal size={16} />
                    </button>
                    <button
                        className="btn"
                        style={{ width: 'auto', background: 'transparent', border: '1px solid var(--glass)', color: 'var(--text-muted)' }}
                        onClick={() => setIsTrashOpen(true)}
                        title="Cestino"
                    >
                        <Trash2 size={16} />
                    </button>
                    <button
                        className="btn"
                        style={{ width: 'auto', background: 'transparent', border: '1px solid var(--glass)', color: 'var(--text-muted)' }}
                        onClick={() => setIsDocStatsOpen(true)}
                        title="Statistiche documenti"
                    >
                        <BarChart2 size={16} />
                    </button>
                    <button
                        className="btn"
                        style={{ width: 'auto', background: 'transparent', border: '1px solid var(--glass)', color: 'var(--text-muted)', fontSize: '0.75rem' }}
                        onClick={() => setIsStatsOpen(true)}
                        title="Cache Redis"
                    >
                        Redis
                    </button>
                    <button
                        className="btn"
                        style={{ width: 'auto', background: 'transparent', border: '1px solid var(--glass)' }}
                        onClick={logout}
                        title="Esci"
                    >
                        <LogOut size={16} />
                    </button>
                </div>
            </nav>

            <main className="container">
                {/* ── Layout principale: sidebar + contenuto ── */}
                <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'flex-start' }}>
                    {showFilters && (
                        <FilterSidebar
                            filters={filters}
                            onChange={(f) => setFilters(f)}
                            onReset={() => setFilters(EMPTY_FILTERS)}
                        />
                    )}

                    <div style={{ flex: 1, minWidth: 0 }}>
                        {/* Barra di ricerca */}
                        <div style={{ position: 'relative', marginBottom: '2rem' }}>
                            <Search style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }} size={18} />
                            <input
                                className="input"
                                style={{ paddingLeft: '3rem', marginBottom: 0 }}
                                placeholder="Cerca per titolo, tag o contenuto…"
                                value={inputValue}
                                onChange={handleSearchChange}
                            />
                        </div>

                        {isLoading ? (
                            <div className="doc-grid">
                                {Array.from({ length: SKELETON_COUNT }).map((_, i) => <SkeletonCard key={i} />)}
                            </div>
                        ) : (
                            <>
                                <div className="doc-grid" key={`${currentPage}-${debouncedQuery}-${JSON.stringify(filters)}`}>
                                    {documents.map((doc: any) => (
                                        <DocumentCard
                                            key={doc.id}
                                            doc={doc}
                                            onDeleted={handleDocDeleted}
                                            onUpdated={handleDocUpdated}
                                        />
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
                    </div>
                </div>
            </main>

            {isUploadOpen && <UploadModal onClose={() => setIsUploadOpen(false)} onSuccess={handleUploadSuccess} />}
            {isBulkOpen && <BulkUploadModal onClose={() => setIsBulkOpen(false)} onSuccess={handleBulkSuccess} />}
            {isStatsOpen && <CacheStatsModal onClose={() => setIsStatsOpen(false)} />}
            {isDocStatsOpen && <StatsWidget onClose={() => setIsDocStatsOpen(false)} />}
            {isTrashOpen && <TrashModal onClose={() => setIsTrashOpen(false)} />}
        </div>
    );
};

export default DashboardPage;
