import React, { useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import { useAuth } from '../store/AuthContext';
import { Search, LogOut, Upload as UploadIcon, FileText, BarChart2, Trash2, Database, Shield } from 'lucide-react';
import DocumentCard from '../components/DocumentCard';
import SkeletonCard from '../components/SkeletonCard';
import Pagination from '../components/Pagination';
import UploadModal from '../components/UploadModal';
import BulkUploadModal from '../components/BulkUploadModal';
import CacheStatsModal from '../components/CacheStatsModal';
import DashboardStatsModal from '../components/DashboardStatsModal';
import SidebarFilters from '../components/SidebarFilters';
import type { FilterState } from '../components/SidebarFilters';
import BulkActionBar from '../components/BulkActionBar';

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
    const [filters, setFilters] = useState<FilterState>({
        tag: null,
        file_type: null,
        date_from: null,
        date_to: null,
        author: null,
        department: null
    });
    const [currentPage, setCurrentPage] = useState(1);
    const [selectedDocs, setSelectedDocs] = useState<string[]>([]);

    const [isUploadOpen, setIsUploadOpen] = useState(false);
    const [isBulkOpen, setIsBulkOpen] = useState(false);
    const [isStatsOpen, setIsStatsOpen] = useState(false);
    const [isDocStatsOpen, setIsDocStatsOpen] = useState(false);
    const { currentUser, logout } = useAuth();

    // Debounce
    useEffect(() => {
        const timer = setTimeout(() => setDebouncedQuery(inputValue), 500);
        return () => clearTimeout(timer);
    }, [inputValue]);

    // Reset to page 1 whenever the search term or filters change
    useEffect(() => {
        setCurrentPage(1);
    }, [debouncedQuery, filters]);

    const offset = (currentPage - 1) * ITEMS_PER_PAGE;

    const { data, isLoading, refetch } = useQuery<PaginatedDocuments>({
        queryKey: ['documents', debouncedQuery, filters, currentPage],
        queryFn: async () => {
            const params = new URLSearchParams({
                limit: String(ITEMS_PER_PAGE),
                offset: String(offset),
            });
            if (debouncedQuery) params.set('query', debouncedQuery);
            if (filters.tag) params.append('tag', filters.tag);
            if (filters.file_type) params.append('file_type', filters.file_type);
            if (filters.date_from) params.append('date_from', filters.date_from);
            if (filters.date_to) params.append('date_to', filters.date_to);
            if (filters.author) params.append('author', filters.author);
            if (filters.department) params.append('department', filters.department);

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

    // Estrai tag, autori e dipartimenti univoci dai documenti
    const { availableTags, availableAuthors, availableDepartments } = React.useMemo(() => {
        const tags = new Set<string>();
        const authors = new Set<string>();
        const depts = new Set<string>();

        documents.forEach((doc: any) => {
            const docTags = doc.doc_metadata?.tags || [];
            docTags.forEach((t: string) => tags.add(t));

            if (doc.doc_metadata?.author) authors.add(doc.doc_metadata.author);
            if (doc.doc_metadata?.dept) depts.add(doc.doc_metadata.dept);
        });

        if (filters.tag) tags.add(filters.tag);
        if (filters.author) authors.add(filters.author);
        if (filters.department) depts.add(filters.department);

        return {
            availableTags: Array.from(tags).sort(),
            availableAuthors: Array.from(authors).sort(),
            availableDepartments: Array.from(depts).sort()
        };
    }, [documents, filters]);

    const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        setInputValue(e.target.value);
    }, []);

    const toggleDocSelection = useCallback((id: string) => {
        setSelectedDocs(prev =>
            prev.includes(id) ? prev.filter(docId => docId !== id) : [...prev, id]
        );
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
            {/* ── Navbar ── */}
            <nav className="nav">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <FileText className="primary" />
                    <h1 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Documentale</h1>
                </div>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                    <button
                        className="btn"
                        style={{ width: 'auto', background: 'transparent', border: '1px solid var(--error)', color: 'var(--error)' }}
                        onClick={() => window.location.href = '/trash'}
                        title="Cestino"
                    >
                        <Trash2 size={18} style={{ marginRight: '0.5rem' }} />
                        Cestino
                    </button>
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
                        style={{ width: 'auto', background: 'transparent', border: '1px solid var(--glass)', color: 'var(--text-muted)' }}
                        onClick={() => setIsDocStatsOpen(true)}
                        title="Statistiche Documenti"
                    >
                        <BarChart2 size={18} />
                    </button>
                    <button
                        className="btn"
                        style={{ width: 'auto', background: 'transparent', border: '1px solid var(--glass)', color: 'var(--accent)' }}
                        onClick={() => setIsStatsOpen(true)}
                        title="Statistiche cache Redis"
                    >
                        <Database size={18} />
                    </button>
                    <button
                        className="btn"
                        style={{ width: 'auto', background: 'transparent', border: '1px solid var(--glass)' }}
                        onClick={logout}
                        title="Esci"
                    >
                        <LogOut size={16} />
                    </button>
                    {/* @ts-ignore - Ignore type error if typing is strict on UserRole */}
                    {currentUser?.role === 'ADMIN' && (
                        <button
                            className="btn"
                            style={{ width: 'auto', background: 'var(--accent)', color: 'var(--bg-dark)', border: 'none', marginLeft: '0.5rem' }}
                            onClick={() => window.location.href = '/admin'}
                            title="Pannello Amministratore"
                        >
                            <Shield size={16} />
                        </button>
                    )}
                </div>
            </nav>

            <main className="container">
                <div className="dashboard-layout">
                    {/* Sidebar Filtri */}
                    <SidebarFilters
                        availableTags={availableTags}
                        availableAuthors={availableAuthors}
                        availableDepartments={availableDepartments}
                        filters={filters}
                        onChange={setFilters}
                    />

                    {/* Contenuto Principale */}
                    <div className="main-content">
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
                            <div className="doc-grid" style={{ marginTop: '1rem' }}>
                                {Array.from({ length: SKELETON_COUNT }).map((_, i) => (
                                    <SkeletonCard key={i} />
                                ))}
                            </div>
                        ) : (
                            <>
                                {/* key forces CSS page-enter animation on page/query change */}
                                <div className="doc-grid" key={`${currentPage}-${debouncedQuery}-${selectedTag}`} style={{ marginTop: '1rem' }}>
                                    {documents.map((doc: any) => (
                                        <DocumentCard
                                            key={doc.id}
                                            doc={doc}
                                            onUpdate={refetch}
                                            isSelected={selectedDocs.includes(doc.id)}
                                            onToggleSelect={toggleDocSelection}
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

            <BulkActionBar
                selectedIds={selectedDocs}
                onClearSelection={() => setSelectedDocs([])}
            />

            {isUploadOpen && (
                <UploadModal onClose={() => setIsUploadOpen(false)} onSuccess={handleUploadSuccess} />
            )}
            {isBulkOpen && (
                <BulkUploadModal onClose={() => setIsBulkOpen(false)} onSuccess={handleBulkSuccess} />
            )}
            {isStatsOpen && (
                <CacheStatsModal onClose={() => setIsStatsOpen(false)} />
            )}
            {isDocStatsOpen && (
                <DashboardStatsModal onClose={() => setIsDocStatsOpen(false)} />
            )}
        </div>
    );
};

export default DashboardPage;
