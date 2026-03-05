import React, { useState, useEffect, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { useAuth } from '../store/AuthContext';
import { Search, LogOut, Upload as UploadIcon, FileText, BarChart3, Trash2, Shield, Bot, LayoutGrid, LayoutList, Sparkles } from 'lucide-react';
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
import { useWebSocket } from '../hooks/useWebSocket';

const ITEMS_PER_PAGE = 20;
const SKELETON_COUNT = 6;

interface Document {
    id: string;
    title: string;
    owner_id: string;
    is_deleted: boolean;
    is_restricted: boolean;
    is_indexed: boolean;
    created_at: string;
    doc_metadata?: {
        tags?: string[];
        author?: string;
        dept?: string;
    };
}

interface PaginatedDocuments {
    items: Document[];
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
    const [chatDoc, setChatDoc] = useState<{ id?: string, title: string } | null>(null);
    const [chatDocked, setChatDocked] = useState(false);
    const [focusDoc, setFocusDoc] = useState<Document | null>(null);
    const { currentUser, logout } = useAuth();

    // Vista griglia o lista
    const [viewMode, setViewMode] = useState<'grid' | 'list'>(() => {
        return (localStorage.getItem('docViewMode') as 'grid' | 'list') || 'grid';
    });

    const handleViewMode = (mode: 'grid' | 'list') => {
        setViewMode(mode);
        localStorage.setItem('docViewMode', mode);
    };

    // WebSocket Notifications
    const { lastMessage } = useWebSocket();
    const [toast, setToast] = useState<{ message: string, id: number } | null>(null);

    useEffect(() => {
        if (lastMessage && lastMessage.type === 'DOCUMENT_INGESTED') {
            setTimeout(() => setToast({ message: lastMessage.message || 'Nuovo documento importato', id: Date.now() }), 0);
            queryClient.invalidateQueries({ queryKey: ['documents'] });

            const timer = setTimeout(() => setToast(null), 5000);
            return () => clearTimeout(timer);
        }
    }, [lastMessage, queryClient]);

    // Debounce
    useEffect(() => {
        const timer = setTimeout(() => setDebouncedQuery(inputValue), 500);
        return () => clearTimeout(timer);
    }, [inputValue]);

    // Reset to page 1 whenever the search term or filters change
    useEffect(() => {
        // Use setTimeout to avoid synchronous setState warning in some lint rules
        const t = setTimeout(() => setCurrentPage(1), 0);
        return () => clearTimeout(t);
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

    const documents = data?.items || [];

    const total = data?.total ?? 0;
    const totalPages = Math.max(1, Math.ceil(total / ITEMS_PER_PAGE));

    // Client-side AI status filtering
    const filteredDocuments = React.useMemo(() => {
        if (filters.ai_status === 'all') return documents;
        return documents.filter((doc: Document) =>
            filters.ai_status === 'ready' ? doc.is_indexed === true : doc.is_indexed !== true
        );
    }, [documents, filters.ai_status]);

    // Estrai tag, autori e dipartimenti univoci dai documenti
    const { availableTags, availableAuthors, availableDepartments } = React.useMemo(() => {
        const tags = new Set<string>();
        const authors = new Set<string>();
        const depts = new Set<string>();

        documents.forEach((doc: Document) => {
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
                <div className="flex-center-gap">
                    <FileText className="primary" />
                    <h1 className="text-125rem-bold">Documentale</h1>
                </div>
                <div className="flex-center-gap-large">
                    <button
                        className="btn btn-trash"
                        onClick={() => window.location.href = '/trash'}
                        title="Cestino"
                    >
                        <Trash2 size={18} className="margin-right-sm" />
                        Cestino
                    </button>
                    <button className="btn btn-auto-width" onClick={() => setIsBulkOpen(true)} title="Importazione di massa">
                        <UploadIcon size={16} className="margin-right-xs" />
                        Cartella
                    </button>
                    <button
                        className="btn btn-outline-accent"
                        onClick={() => setIsUploadOpen(true)}
                        title="Carica un singolo file"
                    >
                        <UploadIcon size={16} className="margin-right-xs" />
                        File
                    </button>
                    <button
                        className="btn btn-outline-accent"
                        onClick={() => setIsDocStatsOpen(true)}
                        title="Statistiche Documenti"
                    >
                        <BarChart3 size={16} className="margin-right-xs" />
                        Dashboard
                    </button>
                    <button
                        className="btn btn-outline-accent"
                        onClick={() => setIsStatsOpen(true)}
                        title="Statistiche cache Redis"
                    >
                        <Bot size={16} className="margin-right-xs" />
                        AI Stats
                    </button>
                    <button
                        className="btn btn-outline-glass"
                        onClick={logout}
                        title="Esci"
                    >
                        <LogOut size={16} />
                    </button>
                    {/* @ts-expect-error - Ignore type error if typing is strict on UserRole */}
                    {currentUser?.role === 'ADMIN' && (
                        <button
                            className="btn btn-admin-panel"
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
                        <div className="search-container">
                            <div className="search-input-wrapper">
                                <Search className="search-icon-pos" size={20} />
                                <input
                                    className="input search-input-field"
                                    data-testid="search-input"
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
                                        {filteredDocuments.map((doc: Document) => (
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
                                        {filteredDocuments.map((doc: Document) => (
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
                selectedTitles={documents?.filter((d: Document) => selectedDocs.includes(d.id)).map((d: Document) => d.title)}
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
                documentIds={selectedDocs}
                docked={chatDocked}
                onToggleDock={() => setChatDocked(d => !d)}
                onOpenDocument={(docId, docTitle) => setChatDoc({ id: docId, title: docTitle })}
            />

            {/* Live Notifications Toast */}
            {toast && (
                <div className="toast-notification">
                    <Sparkles size={20} />
                    <span style={{ fontWeight: 600 }}>{toast.message}</span>
                    <button
                        onClick={() => setToast(null)}
                        className="toast-close-btn"
                        title="Chiudi notifica"
                    >
                        &times;
                    </button>
                </div>
            )}
        </div>
    );
};

export default DashboardPage;
