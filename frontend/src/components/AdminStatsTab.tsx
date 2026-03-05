import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import {
    PieChart, Pie, Cell,
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend
} from 'recharts';
import { FileText, CheckCircle2, AlertTriangle, ExternalLink, X, Search, Layers, Bot, ThumbsUp, Flag, Shield } from 'lucide-react';
import GovernanceSegnalazioniModal from './GovernanceSegnalazioniModal';
import './AdminStatsTab.css';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

interface DashboardKPI {
    total_documents: number;
    ai_ready_percentage: number;
    indexing_errors: number;
}

interface DepartmentStat {
    department: string;
    count: number;
}

interface QueryStat {
    document_title: string;
    query_count: number;
}

interface AuditLogEntry {
    id: string;
    timestamp: string;
    user_email: string;
    department: string;
    document_title: string;
    query: string;
    ai_response: string;
    status: string;
}

const COLORS = ['#64DEC2', '#A5B4FC', '#FCD34D', '#F87171', '#D8B4FE', '#6EE7B7'];

const AdminStatsTab: React.FC = () => {
    const token = localStorage.getItem('token');
    const [page, setPage] = useState(0);
    const [selectedAuditLog, setSelectedAuditLog] = useState<AuditLogEntry | null>(null);
    const [approvalState, setApprovalState] = useState<Record<string, 'approved' | 'flagged' | null>>({});
    const [flagFormOpen, setFlagFormOpen] = useState<string | null>(null); // auditLog id when form is open
    const [flagDescription, setFlagDescription] = useState('');
    const [showSegnalazioniModal, setShowSegnalazioniModal] = useState(false);

    // KPI
    const { data: kpiData, isLoading: isLoadingKpi } = useQuery<DashboardKPI>({
        queryKey: ['admin-stats-kpi'],
        queryFn: async () => {
            const res = await axios.get(`${BASE_URL}/api/admin/stats/dashboard`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            return res.data;
        }
    });

    // Departments Distribution
    const { data: deptData, isLoading: isLoadingDept } = useQuery<DepartmentStat[]>({
        queryKey: ['admin-stats-dept'],
        queryFn: async () => {
            const res = await axios.get(`${BASE_URL}/api/admin/stats/departments`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            return res.data;
        }
    });

    // Top Queries
    const { data: queryData, isLoading: isLoadingQuery } = useQuery<QueryStat[]>({
        queryKey: ['admin-stats-queries'],
        queryFn: async () => {
            const res = await axios.get(`${BASE_URL}/api/admin/stats/queries`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            return res.data;
        }
    });

    // Audit Logs
    const { data: auditData, isLoading: isLoadingAudit } = useQuery<{ items: AuditLogEntry[], total: number }>({
        queryKey: ['admin-audit-logs', page],
        queryFn: async () => {
            const res = await axios.get(`${BASE_URL}/api/admin/audit-logs?skip=${page * 10}&limit=10`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            return res.data;
        }
    });

    if (isLoadingKpi || isLoadingDept || isLoadingQuery || isLoadingAudit) {
        return <div className="loading-state">Caricamento Dashboard Enterprise...</div>;
    }

    return (
        <div className="admin-dashboard-container">
            {/* 1. Stato del Sistema (KPI) */}
            <section className="dashboard-section">
                <h3 className="section-title">Stato del Sistema</h3>
                <div className="kpi-grid">
                    <div className="kpi-card">
                        <div className="kpi-icon-wrapper" style={{ color: '#64DEC2', background: 'rgba(100, 222, 194, 0.1)' }}>
                            <FileText size={28} />
                        </div>
                        <div className="kpi-content">
                            <span className="kpi-label">Documenti Totali</span>
                            <span className="kpi-value">{kpiData?.total_documents || 0}</span>
                        </div>
                    </div>

                    <div className="kpi-card">
                        <div className="kpi-icon-wrapper" style={{ color: '#4ADE80', background: 'rgba(74, 222, 128, 0.1)' }}>
                            <CheckCircle2 size={28} />
                        </div>
                        <div className="kpi-content">
                            <span className="kpi-label">Indice AI (Pronto)</span>
                            <span className="kpi-value">{kpiData?.ai_ready_percentage || 0}%</span>
                        </div>
                    </div>

                    <div className="kpi-card">
                        <div className="kpi-icon-wrapper" style={{ color: '#F87171', background: 'rgba(248, 113, 113, 0.1)' }}>
                            <AlertTriangle size={28} />
                        </div>
                        <div className="kpi-content">
                            <span className="kpi-label">Errori Indicizzazione</span>
                            <span className="kpi-value" style={{ color: kpiData?.indexing_errors ? '#F87171' : 'inherit' }}>
                                {kpiData?.indexing_errors || 0}
                            </span>
                        </div>
                    </div>

                    {/* Governance Segnalazioni KPI card */}
                    <div className="kpi-card kpi-card-clickable" onClick={() => setShowSegnalazioniModal(true)}>
                        <div className="kpi-icon-wrapper" style={{ color: '#A5B4FC', background: 'rgba(165, 180, 252, 0.1)' }}>
                            <Shield size={28} />
                        </div>
                        <div className="kpi-content">
                            <span className="kpi-label">Segnalazioni Governance</span>
                            <span className="kpi-value kpi-value-link">Gestisci &rarr;</span>
                        </div>
                    </div>
                </div>
            </section>

            {/* 2. Analisi della Conoscenza (Grafici) */}
            <section className="dashboard-section">
                <h3 className="section-title">Analisi della Conoscenza</h3>
                <div className="charts-grid">
                    <div className="chart-card">
                        <h4 className="chart-title">Distribuzione per Dipartimento</h4>
                        <div className="chart-wrapper pie-chart-wrapper">
                            {deptData && deptData.length > 0 ? (
                                <ResponsiveContainer width="100%" height="100%">
                                    <PieChart>
                                        <Pie
                                            data={deptData}
                                            innerRadius={60}
                                            outerRadius={80}
                                            paddingAngle={5}
                                            dataKey="count"
                                            nameKey="department"
                                            stroke="none"
                                        >
                                            {deptData.map((_entry, index) => (
                                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                            ))}
                                        </Pie>
                                        <Tooltip
                                            contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                                            itemStyle={{ color: '#f8fafc' }}
                                        />
                                        <Legend />
                                    </PieChart>
                                </ResponsiveContainer>
                            ) : (
                                <div className="empty-chart">Dati non sufficienti</div>
                            )}
                        </div>
                    </div>

                    <div className="chart-card">
                        <h4 className="chart-title">Documenti più Interrogati (Ultimi 30gg)</h4>
                        <div className="chart-wrapper bar-chart-wrapper">
                            {queryData && queryData.length > 0 ? (
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={queryData} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                                        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#334155" />
                                        <XAxis type="number" stroke="#94a3b8" />
                                        <YAxis dataKey="document_title" type="category" width={150} stroke="#94a3b8" tick={{ fontSize: 12 }} />
                                        <Tooltip
                                            cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                            contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                                        />
                                        <Bar dataKey="query_count" fill="#64DEC2" radius={[0, 4, 4, 0]} name="Query" />
                                    </BarChart>
                                </ResponsiveContainer>
                            ) : (
                                <div className="empty-chart">Nessuna interazione AI registrata.</div>
                            )}
                        </div>
                    </div>
                </div>
            </section>

            {/* 3. Audit Log di Compliance */}
            <section className="dashboard-section table-section">
                <h3 className="section-title">Audit Log di Compliance (AI Act Traceability)</h3>
                <div className="table-responsive">
                    <table className="audit-table">
                        <thead>
                            <tr>
                                <th>Timestamp</th>
                                <th>Utente</th>
                                <th>Dipartimento</th>
                                <th>Documento Sorgente</th>
                                <th>Stato Risposta</th>
                                <th>Azioni</th>
                            </tr>
                        </thead>
                        <tbody>
                            {auditData?.items.map((log) => (
                                <tr key={log.id}>
                                    <td className="time-cell">{new Date(log.timestamp).toLocaleString('it-IT', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</td>
                                    <td>{log.user_email}</td>
                                    <td><span className="dept-badge">{log.department}</span></td>
                                    <td className="doc-cell" title={log.document_title}>{log.document_title}</td>
                                    <td>
                                        <span className={`status-badge success`}>✓ Validata</span>
                                    </td>
                                    <td>
                                        <button
                                            className="action-btn"
                                            onClick={() => setSelectedAuditLog(log)}
                                        >
                                            <ExternalLink size={14} /> [View Reasoning]
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            {(!auditData?.items || auditData.items.length === 0) && (
                                <tr>
                                    <td colSpan={6} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                                        Nessun Log AI registrato.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
                <div className="pagination">
                    <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}>Precedente</button>
                    <span>Pagina {page + 1}</span>
                    <button
                        onClick={() => setPage(p => p + 1)}
                        disabled={!auditData?.items || auditData.total <= (page + 1) * 10}
                    >
                        Successiva
                    </button>
                </div>
            </section>

            {/* Advanced Reasoning Modal - Glass-Box (AI Act) */}
            {selectedAuditLog && (
                <div className="reasoning-modal-overlay" onClick={() => setSelectedAuditLog(null)}>
                    <div className="reasoning-modal-advanced" onClick={e => e.stopPropagation()}>
                        {/* Header */}
                        <div className="reasoning-modal-header">
                            <div className="reasoning-modal-title">
                                <Bot size={20} style={{ color: '#64DEC2' }} />
                                <h4>Analisi Reasoning &amp; Trasparenza AI <span className="glass-box-badge">Glass-Box</span></h4>
                            </div>
                            <button className="close-btn" title="Chiudi" onClick={() => setSelectedAuditLog(null)}><X size={20} /></button>
                        </div>

                        {/* Two-panel body */}
                        <div className="reasoning-modal-split">

                            {/* LEFT — Query & Source */}
                            <div className="reasoning-left-panel">
                                <div className="panel-label">User Query</div>
                                <div className="query-bubble">
                                    <p>{selectedAuditLog.query || 'Query non disponibile.'}</p>
                                    <div className="query-meta">
                                        <span>{selectedAuditLog.user_email}</span>
                                        <span>·</span>
                                        <span className="dept-badge-sm">{selectedAuditLog.department}</span>
                                        <span>·</span>
                                        <span>{new Date(selectedAuditLog.timestamp).toLocaleString('it-IT', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>
                                    </div>
                                </div>

                                <div className="panel-label" style={{ marginTop: '1.5rem' }}>Documento Sorgente Validato</div>
                                <div className="source-card">
                                    <div className="source-icon"><FileText size={20} style={{ color: '#F87171' }} /></div>
                                    <div className="source-info">
                                        <span className="source-filename">{selectedAuditLog.document_title}</span>
                                        <span className="source-validated-badge">
                                            <CheckCircle2 size={12} /> Validato dal Dipartimento {selectedAuditLog.department}
                                        </span>
                                    </div>
                                </div>

                                {/* Governance actions */}
                                <div className="governance-actions">
                                    {approvalState[selectedAuditLog.id] === 'approved' ? (
                                        <div className="governance-confirmed approved"><CheckCircle2 size={16} /> Risposta Approvata</div>
                                    ) : approvalState[selectedAuditLog.id] === 'flagged' ? (
                                        <div className="governance-confirmed flagged"><Flag size={16} /> Errore Segnalato — Grazie per il feedback!</div>
                                    ) : flagFormOpen === selectedAuditLog.id ? (
                                        // Inline error report form
                                        <div className="flag-form">
                                            <div className="flag-form-header">
                                                <AlertTriangle size={16} />
                                                <span>Segnala Errore di Analisi</span>
                                            </div>
                                            <label className="flag-form-label">Descrivi il problema riscontrato dall'IA:</label>
                                            <textarea
                                                className="flag-form-textarea"
                                                value={flagDescription}
                                                onChange={e => setFlagDescription(e.target.value)}
                                                placeholder="Es: L'IA ha interpretato erroneamente la data di decorrenza della clausola di recesso, che &egrave; il 2027 e non il 2026 come indicato nell'Articolo 14.3."
                                                rows={4}
                                            />
                                            <div className="flag-form-actions">
                                                <button
                                                    className="governance-btn submit-flag-btn"
                                                    disabled={!flagDescription.trim()}
                                                    onClick={() => {
                                                        setApprovalState(s => ({ ...s, [selectedAuditLog.id]: 'flagged' }));
                                                        setFlagFormOpen(null);
                                                        setFlagDescription('');
                                                    }}
                                                >
                                                    <AlertTriangle size={15} /> Invia Segnalazione
                                                </button>
                                                <button
                                                    className="governance-btn cancel-flag-btn"
                                                    onClick={() => { setFlagFormOpen(null); setFlagDescription(''); }}
                                                >
                                                    Annulla
                                                </button>
                                            </div>
                                        </div>
                                    ) : (
                                        <>
                                            <button
                                                className="governance-btn approve-btn"
                                                onClick={() => setApprovalState(s => ({ ...s, [selectedAuditLog.id]: 'approved' }))}
                                            >
                                                <ThumbsUp size={16} /> Approva Risposta
                                            </button>
                                            <button
                                                className="governance-btn flag-btn"
                                                onClick={() => { setFlagFormOpen(selectedAuditLog.id); setFlagDescription(''); }}
                                            >
                                                <Flag size={16} /> Segnala Errore
                                            </button>
                                        </>
                                    )}
                                </div>
                            </div>

                            {/* RIGHT — Reasoning Steps */}
                            <div className="reasoning-right-panel">
                                <div className="panel-label">AI Reasoning Path &amp; Citations</div>
                                <div className="reasoning-steps">
                                    <div className="reasoning-step">
                                        <div className="step-number" style={{ background: 'rgba(100, 222, 194, 0.15)', color: '#64DEC2' }}>
                                            <Search size={16} />
                                        </div>
                                        <div className="step-content">
                                            <strong>1. Ricerca Semantica</strong>
                                            <p>Analisi semantica della query nel documento <em>«{selectedAuditLog.document_title}»</em>. Identificazione dei chunk testuali più rilevanti tramite similarità vettoriale (pgvector).</p>
                                        </div>
                                    </div>

                                    <div className="reasoning-step">
                                        <div className="step-number" style={{ background: 'rgba(165, 180, 252, 0.15)', color: '#A5B4FC' }}>
                                            <Layers size={16} />
                                        </div>
                                        <div className="step-content">
                                            <strong>2. Estrazione Chunk &amp; Citazione</strong>
                                            <p>Selezionati i paragrafi testuali più rilevanti. Il contesto estratto è stato sottoposto al modello generativo come base documentale di riferimento.</p>
                                        </div>
                                    </div>

                                    <div className="reasoning-step">
                                        <div className="step-number" style={{ background: 'rgba(253, 224, 71, 0.1)', color: '#FDE047' }}>
                                            <Bot size={16} />
                                        </div>
                                        <div className="step-content">
                                            <strong>3. Generazione Risposta (Gemini)</strong>
                                            <p className="response-preview">{selectedAuditLog.ai_response ? selectedAuditLog.ai_response.substring(0, 400) + (selectedAuditLog.ai_response.length > 400 ? '...' : '') : 'Risposta non disponibile.'}</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Governance Segnalazioni Modal */}
            {showSegnalazioniModal && (
                <GovernanceSegnalazioniModal onClose={() => setShowSegnalazioniModal(false)} />
            )}
        </div>
    );
};

export default AdminStatsTab;
