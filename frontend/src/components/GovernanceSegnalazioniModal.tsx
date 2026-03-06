import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import {
    X, Shield, Filter, Plus, ChevronUp, ChevronDown,
    FileText, StickyNote, CircleCheck, Clock, AlertTriangle, ChevronLeft,
} from 'lucide-react';
import './GovernanceSegnalazioniModal.css';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

// ─── Types ───────────────────────────────────────────────────────────────────

type Stato = 'segnalata' | 'in_revisione' | 'risolta';
type Priorita = 'alta' | 'media' | 'bassa';

interface SegnalazioneHistory {
    id: string;
    action_type: 'created' | 'status_changed' | 'note_added' | 'assigned';
    old_value: string | null;
    new_value: string | null;
    created_at: string;
    created_by: string;
}

interface Segnalazione {
    id: string;
    report_code: string;
    document_title: string;
    document_id: string | null;
    reported_at: string;
    stato: Stato;
    priorita: Priorita;
    note: string | null;
    history?: SegnalazioneHistory[];
    created_by?: string;
    assigned_to?: string | null;
    assigned_to_email?: string;
}

interface User {
    id: string;
    email: string;
    role: string;
}

interface SegnalazioniResponse {
    items: Segnalazione[];
    total: number;
    page: number;
    size: number;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const STATO_CONFIG: Record<Stato, { label: string; icon: React.ReactElement; cls: string }> = {
    segnalata: { label: 'Segnalata', icon: <AlertTriangle size={12} />, cls: 'badge-segnalata' },
    in_revisione: { label: 'In Revisione', icon: <Clock size={12} />, cls: 'badge-in-revisione' },
    risolta: { label: 'Risolta', icon: <CircleCheck size={12} />, cls: 'badge-risolta' },
};

const PRIORITA_CONFIG: Record<Priorita, { label: string; cls: string }> = {
    alta: { label: 'Alta', cls: 'badge-alta' },
    media: { label: 'Media', cls: 'badge-media' },
    bassa: { label: 'Bassa', cls: 'badge-bassa' },
};

function formatDate(iso: string): string {
    const d = new Date(iso);
    return d.toLocaleString('it-IT', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

// ─── Sub-component: Dettaglio Segnalazione Modal (Audit Trail) ────────────────

function DettaglioSegnalazioneModal({
    segnalazioneId,
    onClose,
    token
}: {
    segnalazioneId: string;
    onClose: () => void;
    token: string | null;
}) {
    const qc = useQueryClient();
    const { data: users } = useQuery<User[]>({
        queryKey: ['admin-users'],
        queryFn: () =>
            axios.get(`${BASE_URL}/admin/users`, {
                headers: { Authorization: `Bearer ${token}` }
            }).then(r => r.data),
        enabled: !!token
    });

    const [newNote, setNewNote] = useState('');
    const [selectedAssignee, setSelectedAssignee] = useState<string>('');

    const { data: detail, isLoading } = useQuery<Segnalazione>({
        queryKey: ['governance-segnalazione-detail', segnalazioneId],
        queryFn: () =>
            axios.get(`${BASE_URL}/admin/governance/segnalazioni/${segnalazioneId}`, {
                headers: { Authorization: `Bearer ${token}` }
            }).then(r => r.data),
        enabled: !!segnalazioneId
    });

    const updateMutation = useMutation({
        mutationFn: (payload: { stato?: Stato; note?: string; assigned_to?: string }) =>
            axios.patch(
                `${BASE_URL}/admin/governance/segnalazioni/${segnalazioneId}`,
                payload,
                { headers: { Authorization: `Bearer ${token}` } },
            ),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['governance-segnalazioni'] });
            qc.invalidateQueries({ queryKey: ['governance-segnalazione-detail', segnalazioneId] });
            setNewNote('');
            setSelectedAssignee('');
        },
    });

    const handleAssign = () => {
        if (!selectedAssignee) return;
        updateMutation.mutate({ assigned_to: selectedAssignee });
    };

    const handleAddNote = () => {
        if (!newNote.trim()) return;
        updateMutation.mutate({ note: newNote });
    };

    const handleCloseReport = () => {
        updateMutation.mutate({ stato: 'risolta' });
    };

    if (isLoading || !detail) {
        return (
            <div className="sgn-overlay" onClick={onClose}>
                <div className="sgn-detail-modal" onClick={e => e.stopPropagation()}>
                    <div className="sgn-loading">Caricamento audit esteso...</div>
                </div>
            </div>
        );
    }

    const sc = STATO_CONFIG[detail.stato];
    const pc = PRIORITA_CONFIG[detail.priorita];

    return (
        <div className="sgn-overlay" onClick={onClose}>
            <div className="sgn-detail-modal" onClick={e => e.stopPropagation()}>
                <div className="sgn-detail-header">
                    <h4>Dettaglio Segnalazione #{detail.report_code} ({pc.label} Priorità)</h4>
                    <button className="sgn-icon-btn" aria-label="Chiudi" onClick={onClose}><X size={18} /></button>
                </div>

                <div className="sgn-detail-body">
                    {/* Info Section */}
                    <div className="sgn-detail-info-grid">
                        <div className="sgn-info-label">Documento:</div>
                        <div className="sgn-info-value">{detail.document_title}</div>

                        <div className="sgn-info-label">Data Segnalazione:</div>
                        <div className="sgn-info-value">{formatDate(detail.reported_at)}</div>

                        <div className="sgn-info-label">Stato:</div>
                        <div className="sgn-info-value">
                            <span className={`sgn-inline-badge ${sc.cls}`}>{sc.icon} {sc.label}</span>
                        </div>

                        <div className="sgn-info-label">Segnalato da:</div>
                        <div className="sgn-info-value">{detail.created_by}</div>

                        <div className="sgn-info-label">Assegnato a:</div>
                        <div className="sgn-info-value">
                            <span className="sgn-assignee-text">
                                {detail.assigned_to_email || 'Non assegnato'}
                            </span>
                        </div>
                    </div>

                    <hr className="sgn-divider" />

                    {/* Feedback Governance */}
                    <div className="sgn-section">
                        <h5 className="sgn-section-title">Descrizione del Problema (Feedback Governance)</h5>
                        <div className="sgn-feedback-box">
                            {detail.note || <em className="sgn-muted">Nessuna descrizione iniziale fornita.</em>}
                        </div>
                    </div>

                    {/* Snapshot Reasoning AI */}
                    <div className="sgn-section">
                        <h5 className="sgn-section-title">Snapshot del Reasoning AI (Al momento della segnalazione)</h5>
                        <div className="sgn-snapshot-box">
                            <ol>
                                <li>Ricerca Semantica: <em>(Simulata nel mockup — In attesa di integrazione pipeline)</em> (Score: 0.92)</li>
                                <li>Estrazione Chunk: <em>Articolo di riferimento dal documento...</em></li>
                                <li>Generazione Risposta: <em>'Risposta originale dell'AI prima della segnalazione...'</em></li>
                            </ol>
                        </div>
                    </div>

                    <hr className="sgn-divider" />

                    {/* Timeline Audit */}
                    <div className="sgn-section">
                        <h5 className="sgn-section-title">Cronologia delle Azioni & Audit Trail</h5>
                        <div className="sgn-timeline">
                            {detail.history?.map((h, i) => {
                                let icon = <CircleCheck size={14} className="tl-icon-create" />;
                                let colorCls = "tl-dot-create";
                                let text = "";

                                if (h.action_type === 'created') {
                                    text = `Segnalazione creata da ${h.created_by}`;
                                    colorCls = "tl-dot-create";
                                } else if (h.action_type === 'status_changed') {
                                    icon = <Clock size={14} className="tl-icon-status" />;
                                    colorCls = "tl-dot-status";
                                    const stOld = h.old_value ? STATO_CONFIG[h.old_value as Stato]?.label : '';
                                    const stNew = h.new_value ? STATO_CONFIG[h.new_value as Stato]?.label : '';
                                    text = `Stato cambiato da ${stOld} a: ${stNew} (${h.created_by})`;
                                } else if (h.action_type === 'note_added') {
                                    icon = <StickyNote size={14} className="tl-icon-note" />;
                                    colorCls = "tl-dot-note";
                                    text = `Nota Interna aggiunta da ${h.created_by}`;
                                } else if (h.action_type === 'assigned') {
                                    icon = <Shield size={14} className="tl-icon-assign" />;
                                    colorCls = "tl-dot-assign";
                                    const assigneeEmail = users?.find(u => u.id === h.new_value)?.email || h.new_value;
                                    text = `Assegnata a: ${assigneeEmail} (${h.created_by})`;
                                } else {
                                    icon = <Shield size={14} className="tl-icon-other" />;
                                    colorCls = "tl-dot-other";
                                    text = `Azione ${h.action_type} da ${h.created_by}`;
                                }

                                return (
                                    <div className="sgn-timeline-item" key={h.id}>
                                        <div className={`sgn-timeline-dot ${colorCls}`}>{icon}</div>
                                        {i < detail.history!.length - 1 && <div className="sgn-timeline-line"></div>}
                                        <div className="sgn-timeline-content">
                                            <div className="sgn-timeline-meta">
                                                {formatDate(h.created_at)} — {text}
                                            </div>
                                            {h.action_type === 'note_added' && h.new_value && (
                                                <div className="sgn-timeline-note-body">"{h.new_value}"</div>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>

                {/* Actions Footer */}
                <div className="sgn-detail-footer">
                    <div className="sgn-detail-actions-left">
                        <div className="sgn-assignment-controls">
                            <select
                                className="sgn-form-select sgn-select-sm"
                                aria-label="Seleziona utente da assegnare"
                                value={selectedAssignee}
                                onChange={e => setSelectedAssignee(e.target.value)}
                            >
                                <option value="">Seleziona Assegnatario...</option>
                                {users?.filter(u => u.id !== detail.assigned_to).map(u => (
                                    <option key={u.id} value={u.id}>{u.email} ({u.role})</option>
                                ))}
                            </select>
                            <button
                                className="sgn-btn sgn-btn-primary sgn-btn-sm"
                                onClick={handleAssign}
                                disabled={!selectedAssignee || updateMutation.isPending}
                            >
                                Assegna
                            </button>
                        </div>

                        <div className="sgn-inline-note-adder">
                            <input
                                type="text"
                                placeholder="Scrivi nota interna..."
                                className="sgn-form-input sgn-inline-input"
                                value={newNote}
                                onChange={e => setNewNote(e.target.value)}
                                onKeyDown={e => e.key === 'Enter' && handleAddNote()}
                            />
                            <button
                                className="sgn-btn sgn-btn-ghost sgn-margin-l"
                                onClick={handleAddNote}
                                disabled={!newNote.trim() || updateMutation.isPending}
                            >
                                Aggiungi Nota
                            </button>
                        </div>
                    </div>

                    <div className="sgn-detail-actions-right">
                        {detail.stato !== 'risolta' && (
                            <button className="sgn-btn sgn-btn-danger" onClick={handleCloseReport} disabled={updateMutation.isPending}>
                                Chiudi Segnalazione
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

// ─── Sub-component: New Segnalazione Form ─────────────────────────────────────

interface NewFormData {
    document_title: string;
    priorita: Priorita;
    stato: Stato;
    note: string;
}

function NewSegnalazioneForm({ onClose, token }: { onClose: () => void; token: string | null }) {
    const qc = useQueryClient();
    const [form, setForm] = useState<NewFormData>({
        document_title: '',
        priorita: 'media',
        stato: 'segnalata',
        note: '',
    });

    const mutation = useMutation({
        mutationFn: (data: NewFormData) =>
            axios.post(
                `${BASE_URL}/admin/governance/segnalazioni`,
                data,
                { headers: { Authorization: `Bearer ${token}` } },
            ),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['governance-segnalazioni'] });
            onClose();
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.document_title.trim()) return;
        mutation.mutate(form);
    };

    return (
        <div className="sgn-overlay" onClick={onClose}>
            <div className="sgn-new-form-modal" onClick={e => e.stopPropagation()}>
                <div className="sgn-modal-header">
                    <div className="sgn-modal-title">
                        <Plus size={18} style={{ color: '#64DEC2' }} />
                        <h4>Nuova Segnalazione</h4>
                    </div>
                    <button className="sgn-icon-btn" title="Chiudi" aria-label="Chiudi form" onClick={onClose}><X size={18} /></button>
                </div>
                <form className="sgn-new-form-body" onSubmit={handleSubmit}>
                    <label className="sgn-form-label">Documento *</label>
                    <input
                        className="sgn-form-input"
                        type="text"
                        placeholder="Es: Contratto_Quadro_2026.pdf"
                        value={form.document_title}
                        onChange={e => setForm(f => ({ ...f, document_title: e.target.value }))}
                        required
                    />

                    <div className="sgn-form-row">
                        <div className="sgn-form-group">
                            <label className="sgn-form-label">Priorità</label>
                            <select
                                className="sgn-form-select"
                                aria-label="Priorità segnalazione"
                                value={form.priorita}
                                onChange={e => setForm(f => ({ ...f, priorita: e.target.value as Priorita }))}
                            >
                                <option value="alta">🔴 Alta</option>
                                <option value="media">🟡 Media</option>
                                <option value="bassa">🟢 Bassa</option>
                            </select>
                        </div>
                        <div className="sgn-form-group">
                            <label className="sgn-form-label">Stato</label>
                            <select
                                className="sgn-form-select"
                                aria-label="Stato segnalazione"
                                value={form.stato}
                                onChange={e => setForm(f => ({ ...f, stato: e.target.value as Stato }))}
                            >
                                <option value="segnalata">⚠️ Segnalata</option>
                                <option value="in_revisione">⏳ In Revisione</option>
                                <option value="risolta">✅ Risolta</option>
                            </select>
                        </div>
                    </div>

                    <label className="sgn-form-label">Note</label>
                    <textarea
                        className="sgn-form-textarea"
                        rows={4}
                        placeholder="Descrivi il problema riscontrato..."
                        value={form.note}
                        onChange={e => setForm(f => ({ ...f, note: e.target.value }))}
                    />

                    {mutation.isError && (
                        <p className="sgn-error-msg">Errore durante la creazione. Riprova.</p>
                    )}

                    <div className="sgn-form-actions">
                        <button
                            type="submit"
                            className="sgn-btn sgn-btn-primary"
                            disabled={mutation.isPending || !form.document_title.trim()}
                        >
                            {mutation.isPending ? 'Invio...' : 'Crea Segnalazione'}
                        </button>
                        <button type="button" className="sgn-btn sgn-btn-ghost" onClick={onClose}>
                            Annulla
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

// ─── Main Component ───────────────────────────────────────────────────────────

interface Props {
    onClose: () => void;
}

type SortKey = 'report_code' | 'document_title' | 'reported_at' | 'stato' | 'priorita';
type SortDir = 'asc' | 'desc';

const GovernanceSegnalazioniModal: React.FC<Props> = ({ onClose }) => {
    const token = localStorage.getItem('token');
    const qc = useQueryClient();

    // Filter state
    const [filterStato, setFilterStato] = useState<Stato | ''>('');
    const [filterPriorita, setFilterPriorita] = useState<Priorita | ''>('');
    const [showFilter, setShowFilter] = useState(false);
    const [showNewForm, setShowNewForm] = useState(false);
    const [viewDetailId, setViewDetailId] = useState<string | null>(null);
    const [sort, setSort] = useState<{ key: SortKey; dir: SortDir }>({ key: 'reported_at', dir: 'desc' });

    const params = new URLSearchParams({ limit: '50' });
    if (filterStato) params.append('stato', filterStato);
    if (filterPriorita) params.append('priorita', filterPriorita);

    const { data, isLoading } = useQuery<SegnalazioniResponse>({
        queryKey: ['governance-segnalazioni', filterStato, filterPriorita],
        queryFn: () =>
            axios
                .get(`${BASE_URL}/admin/governance/segnalazioni?${params}`, {
                    headers: { Authorization: `Bearer ${token}` },
                })
                .then(r => r.data),
    });

    // Update stato inline
    const updateMutation = useMutation({
        mutationFn: ({ id, stato }: { id: string; stato: Stato }) =>
            axios.patch(
                `${BASE_URL}/admin/governance/segnalazioni/${id}`,
                { stato },
                { headers: { Authorization: `Bearer ${token}` } },
            ),
        onSuccess: () => qc.invalidateQueries({ queryKey: ['governance-segnalazioni'] }),
    });

    // Sort logic
    const sorted = useMemo(() => {
        if (!data?.items) return [];
        const arr = [...data.items];
        arr.sort((a, b) => {
            const va = a[sort.key] ?? '';
            const vb = b[sort.key] ?? '';
            const cmp = String(va).localeCompare(String(vb));
            return sort.dir === 'asc' ? cmp : -cmp;
        });
        return arr;
    }, [data, sort]);

    const toggleSort = (key: SortKey) => {
        setSort(prev =>
            prev.key === key
                ? { key, dir: prev.dir === 'asc' ? 'desc' : 'asc' }
                : { key, dir: 'asc' },
        );
    };

    // Summary counts
    const counts = useMemo(() => {
        const items = data?.items ?? [];
        return {
            totale: data?.total ?? 0,
            in_revisione: items.filter(i => i.stato === 'in_revisione').length,
            risolta: items.filter(i => i.stato === 'risolta').length,
            segnalata: items.filter(i => i.stato === 'segnalata').length,
        };
    }, [data]);

    function SortIcon({ k }: { k: SortKey }) {
        if (sort.key !== k) return <ChevronUp size={12} className="sgn-sort-icon sgn-sort-inactive" />;
        return sort.dir === 'asc'
            ? <ChevronUp size={12} className="sgn-sort-icon" />
            : <ChevronDown size={12} className="sgn-sort-icon" />;
    }

    return (
        <>
            <div className="sgn-overlay" onClick={onClose}>
                <div className="sgn-modal" onClick={e => e.stopPropagation()}>

                    {/* ── Header ── */}
                    <div className="sgn-modal-header">
                        <div className="sgn-modal-title">
                            <Shield size={20} style={{ color: '#64DEC2' }} />
                            <h4>Stato Segnalazioni di Governance AI</h4>
                            <span className="sgn-header-period">Ultimi 30gg</span>
                        </div>
                        <button className="sgn-icon-btn" title="Chiudi" aria-label="Chiudi segnalazioni" onClick={onClose}><X size={20} /></button>
                    </div>

                    {/* ── Summary badges ── */}
                    <div className="sgn-summary-row">
                        <span className="sgn-summary-badge sgn-badge-neutral">{counts.totale} Totali</span>
                        <span className="sgn-summary-badge badge-in-revisione">{counts.in_revisione} In Revisione</span>
                        <span className="sgn-summary-badge badge-risolta">{counts.risolta} Risolte</span>
                        <span className="sgn-summary-badge badge-segnalata">{counts.segnalata} Segnalate</span>
                    </div>

                    {/* ── Toolbar ── */}
                    <div className="sgn-toolbar">
                        <div className="sgn-filter-wrapper">
                            <button
                                className={`sgn-btn sgn-btn-ghost sgn-btn-sm ${showFilter ? 'sgn-btn-active' : ''}`}
                                onClick={() => setShowFilter(v => !v)}
                            >
                                <Filter size={14} /> Filtri
                                {(filterStato || filterPriorita) && <span className="sgn-filter-dot" />}
                            </button>
                            {showFilter && (
                                <div className="sgn-filter-dropdown">
                                    <label className="sgn-form-label">Stato</label>
                                    <select
                                        className="sgn-form-select"
                                        aria-label="Filtra per stato"
                                        value={filterStato}
                                        onChange={e => setFilterStato(e.target.value as Stato | '')}
                                    >
                                        <option value="">Tutti</option>
                                        <option value="segnalata">⚠️ Segnalata</option>
                                        <option value="in_revisione">⏳ In Revisione</option>
                                        <option value="risolta">✅ Risolta</option>
                                    </select>
                                    <label className="sgn-form-label sgn-label-mt">Priorità</label>
                                    <select
                                        className="sgn-form-select"
                                        aria-label="Filtra per priorità"
                                        value={filterPriorita}
                                        onChange={e => setFilterPriorita(e.target.value as Priorita | '')}
                                    >
                                        <option value="">Tutte</option>
                                        <option value="alta">🔴 Alta</option>
                                        <option value="media">🟡 Media</option>
                                        <option value="bassa">🟢 Bassa</option>
                                    </select>
                                    <button
                                        className="sgn-btn sgn-btn-ghost sgn-btn-sm sgn-btn-mt"
                                        onClick={() => { setFilterStato(''); setFilterPriorita(''); setShowFilter(false); }}
                                    >
                                        Reset filtri
                                    </button>
                                </div>
                            )}
                        </div>
                        <button className="sgn-btn sgn-btn-primary sgn-btn-sm" onClick={() => setShowNewForm(true)}>
                            <Plus size={14} /> New Segnalazione
                        </button>
                    </div>

                    {/* ── Table ── */}
                    <div className="sgn-table-wrapper">
                        {isLoading ? (
                            <div className="sgn-loading">Caricamento segnalazioni...</div>
                        ) : (
                            <table className="sgn-table">
                                <thead>
                                    <tr>
                                        <th onClick={() => toggleSort('report_code')} className="sgn-th-sortable">
                                            ID Segnalazione <SortIcon k="report_code" />
                                        </th>
                                        <th onClick={() => toggleSort('document_title')} className="sgn-th-sortable">
                                            Documento <SortIcon k="document_title" />
                                        </th>
                                        <th onClick={() => toggleSort('reported_at')} className="sgn-th-sortable">
                                            Data Segnalazione <SortIcon k="reported_at" />
                                        </th>
                                        <th onClick={() => toggleSort('stato')} className="sgn-th-sortable">
                                            Stato <SortIcon k="stato" />
                                        </th>
                                        <th onClick={() => toggleSort('priorita')} className="sgn-th-sortable">
                                            Priorità <SortIcon k="priorita" />
                                        </th>
                                        <th>Azioni</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {sorted.map(s => {
                                        const sc = STATO_CONFIG[s.stato];
                                        const pc = PRIORITA_CONFIG[s.priorita];
                                        return (
                                            <tr key={s.id}>
                                                <td className="sgn-code-cell">{s.report_code}</td>
                                                <td className="sgn-doc-cell" title={s.document_title}>
                                                    <FileText size={13} style={{ flexShrink: 0 }} />
                                                    {s.document_title}
                                                </td>
                                                <td className="sgn-time-cell">{formatDate(s.reported_at)}</td>
                                                <td>
                                                    <select
                                                        className={`sgn-stato-select ${sc.cls}`}
                                                        aria-label={`Stato segnalazione ${s.report_code}`}
                                                        value={s.stato}
                                                        onChange={e =>
                                                            updateMutation.mutate({ id: s.id, stato: e.target.value as Stato })
                                                        }
                                                    >
                                                        <option value="segnalata">⚠️ Segnalata</option>
                                                        <option value="in_revisione">⏳ In Revisione</option>
                                                        <option value="risolta">✅ Risolta</option>
                                                    </select>
                                                </td>
                                                <td>
                                                    <span className={`sgn-badge ${pc.cls}`}>{pc.label}</span>
                                                </td>
                                                <td>
                                                    <button
                                                        className="sgn-view-note-btn"
                                                        onClick={() => setViewDetailId(s.id)}
                                                        title="Dettaglio e Audit Trail"
                                                    >
                                                        <FileText size={13} /> Dettaglio
                                                    </button>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                    {sorted.length === 0 && (
                                        <tr>
                                            <td colSpan={6} className="sgn-empty-row">
                                                Nessuna segnalazione trovata per il periodo selezionato.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        )}
                    </div>

                    {/* ── Footer ── */}
                    <div className="sgn-footer">
                        <button className="sgn-btn sgn-btn-ghost sgn-btn-sm" onClick={onClose}>
                            <ChevronLeft size={14} /> Chiudi
                        </button>
                        <span className="sgn-footer-count">
                            {sorted.length} di {counts.totale} segnalazioni
                        </span>
                    </div>
                </div>
            </div>

            {/* Sub-modals */}
            {viewDetailId && <DettaglioSegnalazioneModal token={token} segnalazioneId={viewDetailId} onClose={() => setViewDetailId(null)} />}
            {showNewForm && <NewSegnalazioneForm token={token} onClose={() => setShowNewForm(false)} />}
        </>
    );
};

export default GovernanceSegnalazioniModal;
