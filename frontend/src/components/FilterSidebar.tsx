import React from 'react';
import { SlidersHorizontal, X } from 'lucide-react';

export interface Filters {
    file_type: string;
    date_from: string;
    date_to: string;
}

interface Props {
    filters: Filters;
    onChange: (f: Filters) => void;
    onReset: () => void;
}

const FILE_TYPES = [
    { label: 'Tutti', value: '' },
    { label: 'PDF', value: 'application/pdf' },
    { label: 'Word (DOCX)', value: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' },
    { label: 'Testo', value: 'text/plain' },
    { label: 'JPEG', value: 'image/jpeg' },
    { label: 'PNG', value: 'image/png' },
];

const FilterSidebar: React.FC<Props> = ({ filters, onChange, onReset }) => {
    const hasActive = filters.file_type || filters.date_from || filters.date_to;

    return (
        <aside className="filter-sidebar">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600 }}>
                    <SlidersHorizontal size={16} /> Filtri
                </span>
                {hasActive && (
                    <button className="icon-btn" onClick={onReset} title="Azzera filtri" style={{ fontSize: '0.75rem', color: 'var(--error)' }}>
                        <X size={14} /> Azzera
                    </button>
                )}
            </div>

            <label className="filter-label">Tipo file</label>
            <select
                className="input"
                style={{ marginBottom: '1rem' }}
                value={filters.file_type}
                onChange={(e) => onChange({ ...filters, file_type: e.target.value })}
            >
                {FILE_TYPES.map((ft) => (
                    <option key={ft.value} value={ft.value}>{ft.label}</option>
                ))}
            </select>

            <label className="filter-label">Data da</label>
            <input
                type="date"
                className="input"
                style={{ marginBottom: '1rem' }}
                value={filters.date_from}
                onChange={(e) => onChange({ ...filters, date_from: e.target.value })}
            />

            <label className="filter-label">Data a</label>
            <input
                type="date"
                className="input"
                value={filters.date_to}
                onChange={(e) => onChange({ ...filters, date_to: e.target.value })}
            />
        </aside>
    );
};

export default FilterSidebar;
