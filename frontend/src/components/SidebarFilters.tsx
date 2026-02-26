import React from 'react';
import { Filter, X } from 'lucide-react';

interface SidebarFiltersProps {
    availableTags: string[];
    selectedTag: string | null;
    onSelectTag: (tag: string | null) => void;
    // can be expanded later for:
    // showRestricted: boolean;
    // onToggleRestricted: (val: boolean) => void;
}

const SidebarFilters: React.FC<SidebarFiltersProps> = ({ availableTags, selectedTag, onSelectTag }) => {
    return (
        <aside className="sidebar-filters">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
                <Filter size={20} color="var(--accent)" />
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>Filtri Ricerca</h3>
            </div>

            <div className="filter-group">
                <h4 style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Tag</h4>

                {selectedTag && (
                    <button
                        onClick={() => onSelectTag(null)}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            background: 'rgba(239, 68, 68, 0.1)',
                            color: 'var(--error)',
                            border: '1px solid rgba(239, 68, 68, 0.2)',
                            borderRadius: '20px',
                            padding: '0.25rem 0.75rem',
                            fontSize: '0.85rem',
                            cursor: 'pointer',
                            marginBottom: '1rem',
                            width: 'fit-content'
                        }}
                    >
                        <X size={14} /> Azzera Filtro Tag
                    </button>
                )}

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {availableTags.length === 0 ? (
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Nessun tag disponibile</span>
                    ) : (
                        availableTags.map(tag => (
                            <label key={tag} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.95rem' }}>
                                <input
                                    type="radio"
                                    name="filter_tag"
                                    checked={selectedTag === tag}
                                    onChange={() => onSelectTag(tag)}
                                    style={{ accentColor: 'var(--accent)', width: '1rem', height: '1rem' }}
                                />
                                {tag}
                            </label>
                        ))
                    )}
                </div>
            </div>

            {/* Più avanti si possono aggiungere filtri Dipartimento, Tipo di File, Miei/Tutti */}

        </aside>
    );
};

export default SidebarFilters;
