import React, { useState, useEffect, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { useAuth } from '../store/AuthContext';
import { Search, LogOut, Upload as UploadIcon, FileText, BarChart2, Trash2, Database, Shield, Bot, LayoutGrid, LayoutList, Sparkles } from 'lucide-react';
import DocumentCard from '../components/DocumentCard';
import { ChatAssistant } from '../components/ChatAssistant';
import FocusView from '../components/FocusView';
import SkeletonCard from '../components/SkeletonCard';
import Pagination from '../components/Pagination';
import UploadModal from '../components/UploadModal';
import BulkUploadModal from '../components/BulkUploadModal';
import CacheStatsModal from '../components/CacheStatsModal';
import DashboardStatsModal from '../components/DashboardStatsModal';
import SidebarFilters from '../components/SidebarFilters';
import type { FilterState } from '../components/SidebarFilters';
import BulkActionBar from '../components/BulkActionBar';
import DocumentRow from '../components/DocumentRow';

const ITEMS_PER_PAGE = 20;
const SKELETON_COUNT = 6;

interface PaginatedDocuments {
    items: any[];
    total: number;
    limit: number;
    offset: number;
}

const DashboardPage: React.FC = () => {
    const queryClient = useQueryClient();

    const [inputValue, setInputValue] = useState('');
    const [debouncedQuery, setDebouncedQuery] = useState('');
    const [filters, setFilters] = useState<FilterState>({
        tag: null,
        file_type: null,
        date_from: null,
        date_to: null,
        author: null,
        department: null,
        ai_status: 'all'
    });
    const [currentPage, setCurrentPage] = useState(1);
    const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
    const [searchMode, setSearchMode] = useState<'hybrid' | 'semantic'>('hybrid');

    const [isUploadOpen, setIsUploadOpen] = useState(false);
    const [isBulkOpen, setIsBulkOpen] = useState(false);
    const [isStatsOpen, setIsStatsOpen] = useState(false);
    const [isDocStatsOpen, setIsDocStatsOpen] = useState(false);
    const [chatDoc, setChatDoc] = useState<any>(null);
    const [chatDocked, setChatDocked] = useState(false);
    const [focusDoc, setFocusDoc] = useState<any>(null);
    const { currentUser, logout } = useAuth();

    // Vista griglia o lista
    const [viewMode, setViewMode] = useState<'grid' | 'list'>(() => {
        return (localStorage.getItem('docViewMode') as 'grid' | 'list') || 'grid';
    });

    const handleViewMode = (mode: 'grid' | 'list') => {
        setViewMode(mode);
        localStorage.setItem('docViewMode', mode);
    };

    // Debounce
    useEffect(() => {
        const timer = setTimeout(() => setDebouncedQuery(inputValue), 500);
        return () => clearTimeout(timer);
    }, [inputValue]);

    // Reset to page 1 whenever the search term or filters change
    useEffect(() => {
        setCurrentPage(1);
    }, [debouncedQuery, filters, searchMode]);

    const offset = (currentPage - 1) * ITEMS_PER_PAGE;

    const { data, isLoading, refetch } = useQuery<PaginatedDocuments>({
        queryKey: ['documents', debouncedQuery, filters, currentPage, searchMode],
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
            if (searchMode === 'semantic') params.append('mode', 'semantic');

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

    // Client-side AI status filtering
    const filteredDocuments = React.useMemo(() => {
        if (filters.ai_status === 'all') return documents;
        return documents.filter((doc: any) =>
            filters.ai_status === 'ready' ? doc.is_indexed === true : doc.is_indexed !== true
        );
    }, [documents, filters.ai_status]);

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

    // ── Focus Mode ──
    if (focusDoc) {
        return (
            <div>
                <FocusView doc={focusDoc} onClose={() => setFocusDoc(null)} />
            </div>
        );
    }

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
                        className="btn btn-trash"
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
                <div className={`dashboard-layout${chatDocked && !!chatDoc ? ' docked' : ''}`}>
                    {/* Sidebar Filtri */}
                    <SidebarFilters
                        availableTags={availableTags}
                        availableAuthors={availableAuthors}
                        availableDepartments={availableDepartments}
                        filters={filters}
                        onChange={setFilters}
                        onTagAssigned={() => queryClient.invalidateQueries({ queryKey: ['documents'] })}
                    />

                    {/* Contenuto Principale */}
                    <div className="main-content">
                        {/* Search bar + semantic toggle */}
                        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
                            <div style={{ position: 'relative', flex: 1 }}>
                                <Search style={{ position: 'absolute', left: '1rem', top: '1rem', color: 'var(--text-muted)' }} size={20} />
                                <input
                                    className="input"
                                    style={{ paddingLeft: '3rem', marginBottom: 0 }}
                                    placeholder={searchMode === 'semantic' ? 'Ricerca semantica AI…' : 'Cerca documenti per titolo, tag o contenuto…'}
                                    value={inputValue}
                                    onChange={handleSearchChange}
                                />
                            </div>
                            <button
                                className={`search-mode-toggle${searchMode === 'semantic' ? ' active' : ''}`}
                                onClick={() => setSearchMode(m => m === 'hybrid' ? 'semantic' : 'hybrid')}
                                title={searchMode === 'semantic' ? 'Modalità: Ricerca Semantica AI' : 'Modalità: Ricerca Ibrida (testo + AI)'}
                            >
                                <Sparkles size={16} />
                                <span>{searchMode === 'semantic' ? 'AI' : 'Ibrida'}</span>
                            </button>
                        </div>

                        {/* Toolbar: count + view toggle */}
                        <div className="view-toolbar">
                            <p className="doc-count">{total} document{total !== 1 ? 'i' : 'o'}</p>
                            <div className="view-toggle">
                                <button
                                    className={`view-toggle-btn${viewMode === 'grid' ? ' active' : ''}`}
                                    onClick={() => handleViewMode('grid')}
                                    title="Vista Griglia"
                                ><LayoutGrid size={17} /></button>
                                <button
                                    className={`view-toggle-btn${viewMode === 'list' ? ' active' : ''}`}
                                    onClick={() => handleViewMode('list')}
                                    title="Vista Lista"
                                ><LayoutList size={17} /></button>
                            </div>
                        </div>

                        {isLoading ? (
                            <div className="doc-grid">
                                {Array.from({ length: SKELETON_COUNT }).map((_, i) => (
                                    <SkeletonCard key={i} />
                                ))}
                            </div>
                        ) : (
                            <>
                                {viewMode === 'grid' ? (
                                    <div className="doc-grid" key={`${currentPage}-${debouncedQuery}-${filters.tag}`}>
                                        {filteredDocuments.map((doc: any) => (
                                            <DocumentCard
                                                key={doc.id}
                                                doc={doc}
                                                onUpdate={refetch}
                                                isSelected={selectedDocs.includes(doc.id)}
                                                onToggleSelect={toggleDocSelection}
                                                onChatOpen={setChatDoc}
                                                onPreview={setFocusDoc}
                                            />
                                        ))}
                                        {documents.length === 0 && (
                                            <div style={{ textAlign: 'center', gridColumn: '1/-1', color: 'var(--text-muted)', marginTop: '4rem' }}>
                                                Nessun documento trovato.
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <div className="doc-list" key={`${currentPage}-${debouncedQuery}-${filters.tag}`}>
                                        {filteredDocuments.map((doc: any) => (
                                            <DocumentRow
                                                key={doc.id}
                                                doc={doc}
                                                onUpdate={refetch}
                                                isSelected={selectedDocs.includes(doc.id)}
                                                onToggleSelect={toggleDocSelection}
                                                onChatOpen={setChatDoc}
                                                onPreview={setFocusDoc}
                                            />
                                        ))}
                                        {documents.length === 0 && (
                                            <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '4rem' }}>
                                                Nessun documento trovato.
                                            </div>
                                        )}
                                    </div>
                                )}

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

            {/* Modals */}
            <BulkActionBar
                selectedIds={selectedDocs}
                onClearSelection={() => setSelectedDocs([])}
                onSuccess={refetch}
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

            {/* Global FAB for general AI chat */}
            <button
                className="chat-fab"
                onClick={() => setChatDoc({ id: undefined, title: 'Generale' })}
                onMouseOver={(e) => (e.currentTarget.style.transform = 'scale(1.1)')}
                onMouseOut={(e) => (e.currentTarget.style.transform = 'scale(1)')}
                title="Google Gemini Assistant"
            >
                <Bot size={28} />
            </button>

            <ChatAssistant
                isOpen={!!chatDoc}
                onClose={() => setChatDoc(null)}
                documentId={chatDoc?.id}
                documentTitle={chatDoc?.title}
                docked={chatDocked}
                onToggleDock={() => setChatDocked(d => !d)}
                onOpenDocument={(docId, docTitle) => setChatDoc({ id: docId, title: docTitle })}
            />
        </div>
    );
};

export default DashboardPage;
