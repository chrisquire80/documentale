import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { X, PieChart as PieIcon, Users, Tag, FileText, Shield } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import api from '../services/api';
import './DashboardStatsModal.css';

interface DocumentStats {
    total_documents: number;
    by_tags: Record<string, number>;
    by_users: Record<string, number>;
    by_department: Record<string, number>;
    open_reports_count: number;
    validatable_count: number;
}

interface Props {
    onClose: () => void;
}

const COLORS = ['#64DEC2', '#A5B4FC', '#FCD34D', '#F87171', '#D8B4FE', '#6EE7B7'];

const StatBox: React.FC<{ icon: React.ReactNode; label: string; value: string | number; color: string }> = ({ icon, label, value, color }) => (
    <div className="stat-box">
        <div className="stat-box-icon" style={{ background: `${color}15`, color: color }}>
            {icon}
        </div>
        <div>
            <div className="stat-box-label">{label}</div>
            <div className="stat-box-value">{value}</div>
        </div>
    </div>
);

const DashboardStatsModal: React.FC<Props> = ({ onClose }) => {
    const queryClient = useQueryClient();

    const { data, isLoading, error } = useQuery<DocumentStats>({
        queryKey: ['doc-stats'],
        queryFn: async () => {
            const res = await api.get('/documents/stats');
            return res.data;
        }
    });

    const bulkValidateMutation = useMutation({
        mutationFn: () => api.post('/documents/bulk-validate'),
        onSuccess: (res: any) => {
            alert(res.data.message);
            queryClient.invalidateQueries({ queryKey: ['doc-stats'] });
            queryClient.invalidateQueries({ queryKey: ['documents'] });
        },
        onError: () => {
            alert("Errore durante la validazione massiva.");
        }
    });

    const deptData = data ? Object.entries(data.by_department).map(([name, value]) => ({ name, value })) : [];

    return (
        <div className="dashboard-stats-overlay" onClick={onClose}>
            <div
                className="auth-card dashboard-stats-modal"
                onClick={e => e.stopPropagation()}
                style={{ maxWidth: '800px', width: '95vw' }}
            >
                {/* Header */}
                <div className="stats-header">
                    <h2 className="stats-title">
                        <PieIcon size={20} style={{ color: 'var(--accent)' }} />
                        Statistiche Documenti & Governance
                    </h2>
                    <button
                        onClick={onClose}
                        className="stats-close-btn"
                        aria-label="Chiudi"
                    >
                        <X size={20} />
                    </button>
                </div>

                {isLoading && (
                    <div className="stats-loading">
                        Caricamento statistiche...
                    </div>
                )}

                {error && (
                    <div className="stats-error">
                        Errore nel caricamento delle statistiche.
                    </div>
                )}

                {data && (
                    <div className="stats-content-list">
                        {/* KPI Principali */}
                        <div className="stats-grid-kpi" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
                            <StatBox
                                icon={<FileText size={24} />}
                                label="Totale Documenti"
                                value={data.total_documents}
                                color="#64DEC2"
                            />
                            <StatBox
                                icon={<Users size={24} />}
                                label="Proprietari Attivi"
                                value={Object.keys(data.by_users).length}
                                color="#A5B4FC"
                            />
                            <StatBox
                                icon={<Shield size={24} />}
                                label="Segnalazioni Aperte"
                                value={data.open_reports_count}
                                color={data.open_reports_count > 0 ? "#F87171" : "#4ADE80"}
                            />
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem' }}>
                            {/* Distribuzione Dipartimenti (Grafico) */}
                            <div>
                                <h3 className="stats-tags-title" style={{ marginBottom: '1rem' }}>
                                    <PieIcon size={16} /> Distribuzione Dipartimenti
                                </h3>
                                <div style={{ height: '250px', width: '100%' }}>
                                    {deptData.length > 0 ? (
                                        <ResponsiveContainer width="100%" height="100%">
                                            <PieChart>
                                                <Pie
                                                    data={deptData}
                                                    cx="50%"
                                                    cy="50%"
                                                    innerRadius={60}
                                                    outerRadius={80}
                                                    paddingAngle={5}
                                                    dataKey="value"
                                                    stroke="none"
                                                >
                                                    {deptData.map((_entry, index) => (
                                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                                    ))}
                                                </Pie>
                                                <Tooltip
                                                    contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff' }}
                                                    itemStyle={{ color: '#fff' }}
                                                />
                                                <Legend />
                                            </PieChart>
                                        </ResponsiveContainer>
                                    ) : (
                                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
                                            Nessun dato dipartimentale.
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Distribuzione Tag */}
                            <div>
                                <h3 className="stats-tags-title" style={{ marginBottom: '1rem' }}>
                                    <Tag size={16} /> Principali Tag
                                </h3>
                                {Object.keys(data.by_tags).length === 0 ? (
                                    <p className="stats-tags-none">Nessun tag assegnato.</p>
                                ) : (
                                    <div className="stats-tags-container">
                                        {Object.entries(data.by_tags).map(([tag, count]) => (
                                            <div key={tag} className="stats-tag-badge">
                                                <span className="stats-tag-label">{tag}</span>
                                                <span className="stats-tag-count">{count}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Automazione Intelligente (Wave 6) */}
                        <div className="automation-section" style={{ marginTop: '2.5rem', padding: '1.5rem', background: 'rgba(99, 102, 241, 0.05)', borderRadius: '1rem', border: '1px solid rgba(99, 102, 241, 0.2)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                                <div style={{ flex: 1 }}>
                                    <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#818cf8' }}>
                                        <Shield size={20} /> Automazione Intelligente
                                    </h3>
                                    <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                                        L'IA ha identificato documenti pronti per la validazione automatica (Confidenza &gt; 90%, Zero Conflitti).
                                    </p>
                                </div>
                                <button
                                    className="btn"
                                    disabled={!data || data.validatable_count === 0 || bulkValidateMutation.isPending}
                                    onClick={() => {
                                        if (window.confirm(`Stai per validare ${data?.validatable_count} documenti. Procedere?`)) {
                                            bulkValidateMutation.mutate();
                                        }
                                    }}
                                    style={{
                                        width: 'auto',
                                        background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                                        boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)',
                                        border: 'none',
                                        padding: '0.75rem 1.5rem',
                                        color: 'white',
                                        fontWeight: 600
                                    }}
                                >
                                    {bulkValidateMutation.isPending ? 'Validazione...' : '🚀 Avvia Validazione Massiva'}
                                </button>
                            </div>

                            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                                <div style={{ flex: 1 }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.85rem' }}>
                                        <span style={{ color: '#10b981', fontWeight: 600 }}>{data.validatable_count} Automabili</span>
                                        <span style={{ color: '#f59e0b', fontWeight: 600 }}>{data.total_documents - data.validatable_count} Da Revisionare</span>
                                    </div>
                                    <div style={{ height: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', overflow: 'hidden', display: 'flex' }}>
                                        <div style={{
                                            width: `${(data.validatable_count / data.total_documents) * 100}%`,
                                            background: '#10b981',
                                            height: '100%'
                                        }} />
                                        <div style={{
                                            width: `${((data.total_documents - data.validatable_count) / data.total_documents) * 100}%`,
                                            background: '#f59e0b',
                                            height: '100%',
                                            opacity: 0.3
                                        }} />
                                    </div>
                                </div>
                                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '1rem', borderRadius: '0.75rem', textAlign: 'center', minWidth: '100px' }}>
                                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>
                                        {data.total_documents > 0 ? Math.round((data.validatable_count / data.total_documents) * 100) : 0}%
                                    </div>
                                    <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Efficienza AI</div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default DashboardStatsModal;
