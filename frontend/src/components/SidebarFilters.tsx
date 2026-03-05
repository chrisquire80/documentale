import React, { useState } from 'react';
import { Filter, X, Calendar, User, Building2, FileType, Sparkles } from 'lucide-react';

export interface FilterState {
    tag: string | null;
    file_type: string | null;
    date_from: string | null;
    date_to: string | null;
    author: string | null;
    department: string | null;
    ai_status: 'all' | 'ready' | 'pending';
}

interface SidebarFiltersProps {
    availableTags: string[];
    availableAuthors: string[];
    availableDepartments: string[];
    filters: FilterState;
    onChange: (newFilters: FilterState) => void;
    onTagAssigned?: () => void;
}

const FILE_TYPES = [
    { label: 'Tutti', value: '' },
    { label: 'PDF', value: 'application/pdf' },
    { label: 'Word (DOCX)', value: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' },
    { label: 'Testo', value: 'text/plain' },
    { label: 'JPEG', value: 'image/jpeg' },
    { label: 'PNG', value: 'image/png' },
];

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

const SidebarFilters: React.FC<SidebarFiltersProps> = ({
    availableTags,
    availableAuthors,
    availableDepartments,
    filters,
    onChange,
    onTagAssigned,
}) => {
    const [dragOverTag, setDragOverTag] = useState<string | null>(null);

    const countActiveFilters = () => {
        let count = 0;
        if (filters.tag) count++;
        if (filters.file_type) count++;
        if (filters.date_from) count++;
        if (filters.date_to) count++;
        if (filters.author) count++;
        if (filters.department) count++;
        return count;
    };

    const hasActive = countActiveFilters() > 0;

    const resetFilters = () => {
        onChange({
            tag: null,
            file_type: null,
            date_from: null,
            date_to: null,
            author: null,
            department: null,
            ai_status: 'all'
        });
    };

    const handleTagDrop = async (tag: string, e: React.DragEvent) => {
        e.preventDefault();
        setDragOverTag(null);
        const docId = e.dataTransfer.getData('application/x-doc-id');
        if (!docId) return;

        try {
            const token = localStorage.getItem('token');
            // PATCH the doc to add the tag
            await fetch(`${BASE_URL}/documents/${docId}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    doc_metadata: { tags: [tag] },
                }),
            });
            onTagAssigned?.();
        } catch (err) {
            console.error('Tag assignment failed:', err);
        }
    };

    return (
        <aside className="sidebar-filters" data-testid="filter-panel">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Filter size={20} color="var(--accent)" />
                    <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>Filtri Ricerca</h3>
                </div>
                {hasActive && (
                    <button
                        onClick={resetFilters}
                        title="Azzera tutti i filtri"
                        className="btn"
                        style={{
                            padding: '0.25rem 0.5rem',
                            fontSize: '0.75rem',
                            background: 'transparent',
                            color: 'var(--error)',
                            border: '1px solid var(--error)',
                            width: 'auto',
                            minWidth: '0'
                        }}
                    >
                        <X size={14} /> Azzera ({countActiveFilters()})
                    </button>
                )}
            </div>

            {/* Tag — drop targets */}
            <div className="filter-group" style={{ marginBottom: '1.5rem' }}>
                <h4 style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    Tag
                    <span style={{ fontSize: '0.65rem', opacity: 0.6, fontWeight: 400, textTransform: 'none' }}>
                        (trascina un documento qui)
                    </span>
                </h4>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '150px', overflowY: 'auto' }}>
                    {availableTags.length === 0 ? (
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Nessun tag</span>
                    ) : (
                        availableTags.map(tag => (
                            <label
                                key={tag}
                                className={`tag-drop-target${dragOverTag === tag ? ' tag-drop-active' : ''}`}
                                style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.95rem' }}
                                onDragOver={(e) => { e.preventDefault(); setDragOverTag(tag); }}
                                onDragLeave={() => setDragOverTag(null)}
                                onDrop={(e) => handleTagDrop(tag, e)}
                            >
                                <input
                                    type="radio"
                                    name="filter_tag"
                                    checked={filters.tag === tag}
                                    onChange={() => onChange({ ...filters, tag: tag })}
                                    style={{ accentColor: 'var(--accent)', width: '1rem', height: '1rem' }}
                                />
                                {tag}
                            </label>
                        ))
                    )}
                </div>
            </div>

            {/* Stato AI */}
            <div className="filter-group" style={{ marginBottom: '1.5rem' }}>
                <h4 style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <Sparkles size={14} /> Stato AI
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {[
                        { label: 'Tutti', value: 'all' as const },
                        { label: '✅ AI Pronto', value: 'ready' as const },
                        { label: '⏳ In elaborazione', value: 'pending' as const },
                    ].map(opt => (
                        <label key={opt.value} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.95rem' }}>
                            <input
                                type="radio"
                                name="filter_ai_status"
                                checked={filters.ai_status === opt.value}
                                onChange={() => onChange({ ...filters, ai_status: opt.value })}
                                style={{ accentColor: 'var(--accent)', width: '1rem', height: '1rem' }}
                            />
                            {opt.label}
                        </label>
                    ))}
                </div>
            </div>

            {/* Tipo File */}
            <div className="filter-group" style={{ marginBottom: '1.5rem' }}>
                <h4 style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <FileType size={14} /> Tipo file
                </h4>
                <select
                    className="input"
                    value={filters.file_type || ''}
                    onChange={(e) => onChange({ ...filters, file_type: e.target.value || null })}
                    style={{ marginBottom: 0, padding: '0.5rem' }}
                >
                    {FILE_TYPES.map((ft) => (
                        <option key={ft.value} value={ft.value}>{ft.label}</option>
                    ))}
                </select>
            </div>

            {/* Tipo Dipartimento */}
            <div className="filter-group" style={{ marginBottom: '1.5rem' }}>
                <h4 style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <Building2 size={14} /> Dipartimento
                </h4>
                <select
                    className="input"
                    value={filters.department || ''}
                    onChange={(e) => onChange({ ...filters, department: e.target.value || null })}
                    style={{ marginBottom: 0, padding: '0.5rem' }}
                >
                    <option value="">Tutti</option>
                    {availableDepartments.map((dept) => (
                        <option key={dept} value={dept}>{dept}</option>
                    ))}
                </select>
            </div>

            {/* Autore */}
            <div className="filter-group" style={{ marginBottom: '1.5rem' }}>
                <h4 style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <User size={14} /> Autore
                </h4>
                <select
                    className="input"
                    value={filters.author || ''}
                    onChange={(e) => onChange({ ...filters, author: e.target.value || null })}
                    style={{ marginBottom: 0, padding: '0.5rem' }}
                >
                    <option value="">Qualsiasi Autore</option>
                    {availableAuthors.map((auth) => (
                        <option key={auth} value={auth}>{auth}</option>
                    ))}
                </select>
            </div>

            {/* Date */}
            <div className="filter-group" style={{ marginBottom: '1.5rem' }}>
                <h4 style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <Calendar size={14} /> Creato in data
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                        Da
                        <input
                            type="date"
                            className="input"
                            style={{ padding: '0.4rem', marginTop: '0.2rem' }}
                            value={filters.date_from || ''}
                            onChange={(e) => onChange({ ...filters, date_from: e.target.value || null })}
                        />
                    </label>
                    <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                        A
                        <input
                            type="date"
                            className="input"
                            style={{ padding: '0.4rem', marginTop: '0.2rem' }}
                            value={filters.date_to || ''}
                            onChange={(e) => onChange({ ...filters, date_to: e.target.value || null })}
                        />
                    </label>
                </div>
            </div>

        </aside>
    );
};

export default SidebarFilters;
