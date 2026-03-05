import React from 'react';
import { useQuery } from '@tanstack/react-query';
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
    const { data, isLoading, error } = useQuery<DocumentStats>({
        queryKey: ['doc-stats'],
        queryFn: async () => {
            const res = await api.get('/documents/stats');
            return res.data;
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
                    </div>
                )}
            </div>
        </div>
    );
};

export default DashboardStatsModal;
